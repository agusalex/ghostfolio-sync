import json
from datetime import datetime

from ibflex import FlexQueryResponse, BuySell

import LoggerFactory
from EnvironmentConfiguration import EnvironmentConfiguration
from GhostfolioApi import GhostfolioApi, \
    GhostfolioTicker, \
    GhostfolioConfig, \
    GhostfolioImportActivity
from IbkrApi import IbkrApi, IbkrConfig

envConf = EnvironmentConfiguration()
logger = LoggerFactory.logger


def get_cash_amount_from_flex(query):
    cash = 0
    try:
        cash += query.FlexStatements[0].CashReport[0].endingCash
    except Exception as e:
        print(e)
    try:
        cash += query.FlexStatements[0].CashReport[0].endingCashPaxos
    except Exception as e:
        print(e)
    return cash


def format_act(act: GhostfolioImportActivity):
    return {
        "accountId": act.account_id,
        "date": act.date[0:18],
        "fee": float(act.fee),
        "quantity": act.quantity,
        "symbol": act.symbol,
        "type": act.type,
        "unitPrice": act.unitPrice,
    }


def is_act_present(
        act_search: GhostfolioImportActivity,
        acts: list[GhostfolioImportActivity]
):
    # if sync has written id as comment,
    # extract it, it could be the transaction id
    comment = act_search.comment

    for act in acts:
        potential_match_comment = act.comment
        if comment is not None \
                and potential_match_comment is not None \
                and comment.startswith(potential_match_comment):
            return True
        act1 = format_act(act)
        act2 = format_act(act_search)
        if act1 == act2:
            return True
    return False


def get_diff(existing_acts, new_acts: list[GhostfolioImportActivity]):
    diff = []
    for new_act in new_acts:
        if not is_act_present(new_act, existing_acts):
            diff.append(new_act)
    return diff


class SyncIBKR:
    # todo: Id as in ghostfolio
    IBKRCATEGORY = None

    def __init__(self, ibkr_config: IbkrConfig, ghost_config: GhostfolioConfig):
        self.ghostfolio_api = GhostfolioApi(ghost_config)
        self.ibkr_api = IbkrApi(ibkr_config)
        self.ghost_currency = ghost_config.currency

    def sync_ibkr(self):
        account = self.ghostfolio_api.create_or_get_ibkr_account()
        account_id = account['id']
        if account_id == "":
            logger.warning("Failed to retrieve account ID closing now")
            return
        query: FlexQueryResponse = self.ibkr_api.get_and_parse_query()
        activities: list[GhostfolioImportActivity] = []
        date_format = "%Y-%m-%d"

        self.set_cash_to_account(account_id, get_cash_amount_from_flex(query))
        skipped_categories_counter = {}
        for trade in query.FlexStatements[0].Trades:

            if trade.assetCategory is not trade.assetCategory.STOCK:
                logger.debug(f"ignore {trade.assetCategory}, {trade.symbol}: {trade}")
                existing_skips = skipped_categories_counter.get(trade.assetCategory, 0)
                skipped_categories_counter[trade.assetCategory] = existing_skips + 1
                continue

            if trade.openCloseIndicator is None:
                logger.warning("trade is not open or close (ignoring): %s", trade)
                continue

            date = datetime.strptime(str(trade.tradeDate), date_format)
            iso_format = date.isoformat()
            symbol = self.map_symbol(trade)
            buy_sell = self.map_buy_sell(trade)

            lookup_ticker: GhostfolioTicker = self. \
                ghostfolio_api.get_ticker(trade.isin, symbol)
            unit_price = float(trade.tradePrice)
            unit_currency = trade.currency
            fee = float(trade.taxes)

            # Handling special case:
            # ghostfolio is checking currency against source (yahoo)
            if trade.currency != lookup_ticker.currency:
                # converting GBP to GBp (IB vs Yahoo)
                if trade.currency == 'GBP' and lookup_ticker.currency == 'GBp':
                    logger.debug("Converting GBP to GBp for Yahoo compatibility")
                    unit_price *= 100
                    unit_currency = 'GBp'
                    if trade.ibCommissionCurrency == 'GBP':
                        fee += float((trade.ibCommission * 100) * -1)
            else:
                fee += float(trade.ibCommission * -1)

            quantity = abs(float(trade.quantity))
            comment = f"<sync-trade-transactionID>" \
                      f"{trade.transactionID}" \
                      f"</sync-trade-transactionID>"

            activities.append(GhostfolioImportActivity(
                unit_currency,
                lookup_ticker.data_source,
                iso_format,
                fee,
                quantity,
                lookup_ticker.symbol,
                buy_sell,
                unit_price,
                account_id,
                comment
            ))

        if len(skipped_categories_counter) > 0:
            logger.info(f"Skipped: {skipped_categories_counter}")

        existing_activities: list[GhostfolioImportActivity] = \
            self.ghostfolio_api.get_all_activities_for_account(account_id)

        diff: list[GhostfolioImportActivity] = get_diff(existing_activities, activities)
        if envConf.is_debug_files_enabled():
            debug_file_folder = envConf.debug_file_location()
            logger.warn("Flag WRITE_DEBUG_FILES is set, writing files")
            with open(f"{debug_file_folder}activities_from_gf.json", 'w') as outfile:
                logger.warn("WRITE_DEBUG_FILES: writing existing_activities")
                json.dump(existing_activities, outfile)
            with open(f"{debug_file_folder}activities_from_ib.json", 'w') as outfile:
                logger.warn("WRITE_DEBUG_FILES: writing new activities")
                json.dump(activities, outfile)
            with open(f"{debug_file_folder}activities_diff.json", 'w') as outfile:
                logger.warn("WRITE_DEBUG_FILES: writing new activities differences")
                json.dump(diff, outfile)

        if len(diff) == 0:
            logger.info("Nothing new to sync")
        else:
            self.ghostfolio_api.import_activities(diff)

    def map_symbol(self, trade):
        symbol = trade.symbol
        if ".USD-PAXOS" in trade.symbol:
            symbol = trade.symbol.replace(".USD-PAXOS", "") + "USD"
        return symbol

    def map_buy_sell(self, trade):
        if trade.buySell == BuySell.BUY:
            buy_sell = "BUY"
        else:
            buy_sell = "SELL"
        return buy_sell

    def set_cash_to_account(self, account_id, cash):
        if cash == 0:
            logger.info("No cash set, no cash retrieved")
            return False
        account = {
            "accountType": "SECURITIES",
            "balance": round(float(cash), 2),
            "id": account_id,
            "currency": self.ghost_currency,
            "isExcluded": False,
            "name": self.ghostfolio_api.account_name,
            "platformId": self.ghostfolio_api.ibkr_platform_id
        }

        self.ghostfolio_api.update_account(account_id, account)

    def delete_all_activities(self):
        account_id = self.ghostfolio_api.create_or_get_ibkr_account()['id']
        if account_id == "":
            logger.warning("Failed to retrieve account ID stopping now")
            return
        self.ghostfolio_api.delete_all_activities(account_id)
