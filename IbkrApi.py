from collections import namedtuple
from datetime import datetime

from diskcache import Cache
from ibflex import client, parser, FlexQueryResponse, CashAction, CashTransaction, Trade
from ibflex.client import ResponseCodeError

import LoggerFactory
from EnvironmentConfiguration import EnvironmentConfiguration

IbkrConfig = namedtuple('IbkrConfig',
                        'token query_id')

logger = LoggerFactory.logger
cache = Cache(directory='.cache/ibkr-api')
envConf = EnvironmentConfiguration()


class IbkrApi:

    def __init__(self, ibkr_config: IbkrConfig):
        self.ibkr_token = ibkr_config.token
        self.ibkr_query = ibkr_config.query_id

    @cache.memoize(expire=3600, tag='query')
    def get_and_parse_query(self):
        logger.debug("Fetching Query")
        try:
            response = client.download(self.ibkr_token, self.ibkr_query)
        except ResponseCodeError as responseCodeError:
            if responseCodeError.code == 1012:
                logger.error("Token Expired! "
                             "see "
                             "https://www.interactivebrokers.com.au/en/?f=asr_statemen"
                             "ts_tradeconfirmations&p=flexqueries4"
                             "renew token in account management: https://www.interactiv"
                             "ebrokers.co.uk/AccountManagement/AmAuthentication?action"
                             "=ManageAccount")
            raise responseCodeError
        if envConf.is_debug_files_enabled():
            self.__query_to_file(response)
        logger.debug("Parsing Query")
        query: FlexQueryResponse = parser.parse(response)
        return query

    @staticmethod
    def get_stock_transactions(query: FlexQueryResponse) -> list[Trade]:
        skipped_categories_counter = {}
        trades: list[Trade] = []
        for flexStatement in query.FlexStatements:
            for trade in flexStatement.Trades:
                if trade.assetCategory is not trade.assetCategory.STOCK:
                    logger.debug(f"ignore {trade.assetCategory}, {trade.symbol}: {trade}")
                    existing_skips = skipped_categories_counter.get(trade.assetCategory, 0)
                    skipped_categories_counter[trade.assetCategory] = existing_skips + 1
                    continue

                if trade.openCloseIndicator is None:
                    logger.warning("trade is not open or close (ignoring): %s", trade)
                    continue

                trades.append(trade)

        if len(skipped_categories_counter) > 0:
            logger.info(f"Skipped: {skipped_categories_counter}")

        return trades

    @staticmethod
    def get_cash_transactions(query) -> list[CashTransaction]:
        cash_action_types: list[CashAction] = [CashAction.DIVIDEND,
                                               CashAction.PAYMENTINLIEU,
                                               CashAction.WHTAX]
        all_cash_transactions = []
        for flex_statements in query.FlexStatements:
            all_cash_transactions.extend(flex_statements.CashTransactions)
        transaction_summaries = filter(
            lambda x: x.levelOfDetail == 'SUMMARY' and (x.type in cash_action_types),
            all_cash_transactions
        )
        return sorted(transaction_summaries, key=lambda t: t.reportDate)

    @staticmethod
    def get_cash_transaction_isin(query):
        cash_transactions: list[CashTransaction] = IbkrApi.get_cash_transactions(query)
        return list(set(map(lambda x: x.isin, cash_transactions)))

    def __query_to_file(self, response):
        timestamp = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"
        folder = envConf.debug_file_location()
        filename = f"{folder}{timestamp}-ib_flex_query-{self.ibkr_query}.xml"
        logger.warning(f"writing query to {filename}")
        with open(filename, 'wb') as outfile:
            outfile.write(response)
