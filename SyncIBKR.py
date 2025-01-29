import json
import re
from datetime import datetime
from typing import Optional

import requests
import yaml
from ibflex import client, parser, FlexQueryResponse, BuySell, FlexStatement, Trade

# Create logger
import logging
logger = logging.getLogger(__name__)


def get_cash_amount_from_flex(account_statement: FlexStatement) -> dict:
    logger.info("Getting cash amount")
    base_currency = account_statement.AccountInformation.currency
    logger.info("Base currency: %s", base_currency)
    cash = {}
    for cash_report_currency in account_statement.CashReport:
        if cash_report_currency.currency == "BASE_SUMMARY":
            try:
                cash[base_currency] = float(cash_report_currency.endingCash)
                logger.info("Cash amount: %s", cash[base_currency])
                return cash
            except Exception as e:
                logger.info(e)
    return cash


def generate_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def format_existing_act(act: dict, symbol_type: str = "symbol") -> dict:
    symbol = act.get("SymbolProfile", {symbol_type: ""}).get(symbol_type)

    if symbol is None or len(symbol) == 0:
        logger.warning("Could not find nested symbol type %s for activity %s: %s",
                       symbol_type, act["id"], act.get("SymbolProfile"))
        symbol = act.get("symbol", "")

    return {
        "accountId": act["accountId"],
        "date": act["date"][0:18],
        "fee": abs(float(act["fee"])),
        "quantity": abs(float(act["quantity"])),
        "symbol": symbol,
        "type": act["type"],
        "unitPrice": act["unitPrice"]
    }


def format_new_act(act: dict, symbol_type: str = "symbol") -> dict:
    return {
        "accountId": act["accountId"],
        "date": act["date"][0:18],
        "fee": abs(float(act["fee"])),
        "quantity": abs(float(act["quantity"])),
        "symbol": act.get(symbol_type, ""),
        "type": act["type"],
        "unitPrice": act["unitPrice"]
    }


def is_act_present(new_act, existing_acts, synced_acts_ids: set):
    # Precise comparison using the IBKR trade id
    comment = new_act["comment"]
    if comment is not None:
        # Extract the tradeID from the comment using regular expressions
        match = re.search(r"tradeID=(\d+)", comment)
        if match:
            trade_id = match.group(1)
            if trade_id in synced_acts_ids:
                return True

    # Legacy comparison
    for existing_act in existing_acts:
        formatted_act = format_existing_act(existing_act, "figi")
        formatted_new_act = format_new_act(new_act, "figi")
        if formatted_act == formatted_new_act:
            return True
        formatted_act = format_existing_act(existing_act, "isin")
        formatted_new_act = format_new_act(new_act)
        if formatted_act == formatted_new_act:
            return True
        formatted_act = format_existing_act(existing_act)
        formatted_new_act = format_new_act(new_act, "ibkrSymbol")
        if formatted_act == formatted_new_act:
            return True
    return False


def get_diff(old_acts, new_acts):
    diff = []
    synced_acts_ids = set()
    for old_act in old_acts:
        comment = old_act["comment"]
        if comment is not None:
            # Extract the tradeID from the comment using regular expressions
            match = re.search(r"tradeID=(\d+)", comment)
            if match:
                trade_id = match.group(1)
                synced_acts_ids.add(trade_id)

    for new_act in new_acts:
        if not is_act_present(new_act, old_acts, synced_acts_ids):
            del new_act["figi"]
            del new_act["ibkrSymbol"]
            diff.append(new_act)
    return diff


class SyncIBKR:
    #IBKRCATEGORY = "66b22c82-a96c-4e4f-aaf2-64b4ca41dda2"

    def __init__(self, ghost_host, ibkrtoken, ibkrquery, ghost_key, ghost_token, ibkr_account_id, ghost_account_name, ghost_currency, ghost_ibkr_platform, mapping_file='mapping.yaml'):
        self.account_id: Optional[str] = None
        if ghost_token == "" and ghost_key != "":
            self.ghost_token = self.create_ghost_token(ghost_host, ghost_key)
        else:
            self.ghost_token = ghost_token

        if self.ghost_token is None or self.ghost_token == "":
            logger.info("No bearer token provided, closing now")
            raise Exception("No bearer token provided")

        self.ghost_host = ghost_host
        self.ibkr_account_id = ibkr_account_id
        self.ghost_account_name = ghost_account_name
        self.ghost_currency = ghost_currency
        self.ibkrtoken = ibkrtoken
        self.ibkrquery = ibkrquery
        self.ibkrplatform = ghost_ibkr_platform

        # Load the configuration file
        with open(mapping_file, 'r') as file:
            config = yaml.safe_load(file)

        # Extract the symbol mapping from the configuration
        self.symbol_mapping = config.get('symbol_mapping', {})

    def sync_ibkr(self):
        logger.info("Fetching Query")
        response = client.download(self.ibkrtoken, self.ibkrquery)
        #logger.info("Parsing Query:\n%s", response)
        query: FlexQueryResponse = parser.parse(response)
        account_statement = self.get_account_flex_statement(query)
        activities = []
        date_format = "%Y-%m-%d %H:%M:%S"
        data_source = "YAHOO"

        try:
            self.ghost_currency = account_statement.AccountInformation.currency
        except Exception as e:
            logger.error("Error getting currency from IBKR account statement: %s", e)

        account_id = self.create_or_get_IBKR_accountId()
        if account_id == "":
            logger.info("Failed to retrieve account ID closing now")
            return
        self.set_cash_to_account(account_id, get_cash_amount_from_flex(account_statement))
        for trade in account_statement.Trades:
            if trade.openCloseIndicator is None:
                logger.info("trade is not open or close (ignoring): %s", trade)
            elif trade.openCloseIndicator.CLOSE:
                date = datetime.strptime(str(trade.dateTime), date_format)
                iso_format = date.isoformat()
                symbol = self.get_symbol_for_trade(trade, data_source)

                if trade.buySell == BuySell.BUY:
                    buysell = "BUY"
                elif trade.buySell == BuySell.SELL:
                    buysell = "SELL"
                else:
                    logger.info("trade is not buy or sell (ignoring): %s", trade)
                    continue

                activities.append({
                    "accountId": account_id,
                    "comment": f"tradeID={trade.tradeID}",
                    "currency": trade.currency,
                    "dataSource": data_source,
                    "date": iso_format,
                    "fee": abs(float(trade.ibCommission)),
                    "quantity": abs(float(trade.quantity)),
                    "symbol": symbol.replace(" ", "-"),
                    "type": buysell,
                    "unitPrice": float(trade.tradePrice),
                    "figi": trade.figi,
                    "ibkrSymbol": self.symbol_mapping[trade.symbol] if trade.symbol in self.symbol_mapping else trade.symbol
                })

        diff = get_diff(self.get_all_acts_for_account(), activities)
        if len(diff) == 0:
            logger.info("Nothing new to sync")
        else:
            self.import_act(diff)

    def get_symbol_for_trade(self, trade: Trade, data_source: str):
        symbol = trade.symbol
        if data_source == "YAHOO":
            if trade.isin is not None and len(trade.isin) > 0:
                symbol = trade.isin # ISIN provides better mapping

        if symbol in self.symbol_mapping:
            logger.info("Transformed symbol %s into %s", symbol, self.symbol_mapping[symbol])
            symbol = self.symbol_mapping[symbol]
        else:
            logger.info("Symbol %s not found in mapping.", symbol)
        return symbol

    def create_ghost_token(self, ghost_host, ghost_key):
        logger.info("No bearer token provided, fetching one")
        token = {
            'accessToken': ghost_key
        }

        url = f"{ghost_host}/api/v1/auth/anonymous"

        payload = json.dumps(token)
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return ""
        if response.status_code == 201:
            logger.info("Bearer token fetched")
            return response.json()["authToken"]
        logger.info("Failed fetching bearer token")
        return ""

    def set_cash_to_account(self, account_id, cash: dict):
        if cash is None or len(cash) == 0:
            logger.info("No cash set, no cash retrieved")
            return False
        for currency, amount in cash.items():
            amount = {
                "balance": amount,
                "id": account_id,
                "currency": currency,
                "isExcluded": False,
                "name": self.ghost_account_name,
                "platformId": self.ibkrplatform
            }
            logger.info("Updating Cash for account " + account_id + ": " + json.dumps(amount))

            url = f"{self.ghost_host}/api/v1/account/{account_id}"

            payload = json.dumps(amount)
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }
            try:
                response = requests.request("PUT", url, headers=headers, data=payload)
            except Exception as e:
                logger.info(e)
                return
            if response.status_code == 200:
                logger.info(f"Updated Cash for account {response.json()['id']}")
            else:
                logger.info("Failed create: " + response.text)

    def delete_act(self, act_id):
        url = f"{self.ghost_host}/api/v1/order/{act_id}"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("DELETE", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return False

        return response.status_code == 200

    def import_act(self, bulk):
        chunks = generate_chunks(sorted(bulk, key=lambda x: x["date"]), 10)
        for acts in chunks:
            logger.info("Adding activities:\n%s", json.dumps(acts, indent=4))

            url = f"{self.ghost_host}/api/v1/import"
            payload = json.dumps({"activities": acts})
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }

            try:
                response = requests.request("POST", url, headers=headers, data=payload)
            except Exception as e:
                logger.info(e)
                return False
            if response.status_code == 201:
                logger.info("Added activities. Response:\n%s", json.dumps(response.json(), indent=4))
            else:
                logger.info("Failed to create: " + response.text)
            if response.status_code != 201:
                return False
        return True

    def addAct(self, act):
        url = f"{self.ghost_host}/api/v1/order"

        payload = json.dumps(act)
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
            'Content-Type': 'application/json'
        }
        logger.info("Adding activity: " + json.dumps(act))
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return False
        if response.status_code == 201:
            logger.info(f"created {response.json()['id']}")
        else:
            logger.info("Failed create: " + response.text)
        return response.status_code == 201

    def create_ibkr_account(self):
        logger.info("Creating IBKR account")
        account = {
            "balance": 0,
            "currency": self.ghost_currency,
            "isExcluded": False,
            "name": self.ghost_account_name,
            "platformId": self.ibkrplatform
        }

        url = f"{self.ghost_host}/api/v1/account"

        payload = json.dumps(account)
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return ""
        if response.status_code == 201:
            logger.info("IBKR account: " + response.json()["id"])
            return response.json()["id"]
        logger.info("Failed creating ")
        return ""

    def get_all_accounts(self):
        logger.info("Finding all accounts")
        url = f"{self.ghost_host}/api/v1/account"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return []
        if response.status_code == 200:
            return response.json()['accounts']
        else:
            raise Exception(response)

    def create_or_get_IBKR_accountId(self):
        if self.account_id is not None:
            return self.account_id

        accounts = self.get_all_accounts()
        logger.info("Accounts: %s", json.dumps(accounts, indent=4))
        for account in accounts:
            if account["name"] == self.ghost_account_name:
                logger.info("IBKR account: %s", account["id"])
                self.account_id = account["id"]
                return account["id"]

        self.account_id = self.create_ibkr_account()
        return self.account_id

    def delete_all_acts(self):
        acts = self.get_all_acts_for_account()

        if not acts:
            logger.info("No activities to delete")
            return True

        url = f"{self.ghost_host}/api/v1/order"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("DELETE",
                                        url,
                                        headers=headers,
                                        params={"accounts": self.create_or_get_IBKR_accountId()},
                                        data=payload)
        except Exception as e:
            logger.info(e)
            return False

        return response.status_code == 200

    def get_all_acts_for_account(self, account_id: str = None, range: str = None, symbol: str = None):
        if account_id is None:
            account_id = self.create_or_get_IBKR_accountId()

        url = f"{self.ghost_host}/api/v1/order"

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
        }
        try:
            response = requests.request("GET",
                                        url,
                                        headers=headers,
                                        params={"accounts": account_id,
                                                "range": range,  # https://github.com/ghostfolio/ghostfolio/blob/main/libs/common/src/lib/types/date-range.type.ts
                                                "symbol": symbol},
                                        data=payload)
        except Exception as e:
            logger.info(e)
            return []

        if response.status_code == 200:
            return response.json()['activities']
        else:
            return []

    def get_account_flex_statement(self, query: FlexQueryResponse) -> FlexStatement:
        return next(
            (flex_statement for flex_statement in query.FlexStatements if flex_statement.accountId == self.ibkr_account_id),
            None)
