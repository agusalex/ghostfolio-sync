import json
import re
import time
import hmac
import hashlib
from datetime import datetime
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)


def generate_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def format_existing_act(act: dict, symbol_type: str = "symbol") -> dict:
    symbol = act.get("SymbolProfile", {symbol_type: ""}).get(symbol_type)
    if not symbol:
        logger.warning("Could not find nested symbol type %s for activity %s: %s",
                       symbol_type, act.get("id"), act.get("SymbolProfile"))
        symbol = act.get("symbol", "")
    return {
        "accountId": act["accountId"],
        "date": act["date"][:18],
        "fee": abs(float(act["fee"])),
        "quantity": abs(float(act["quantity"])),
        "symbol": symbol,
        "type": act["type"],
        "unitPrice": act["unitPrice"]
    }


def format_new_act(act: dict, symbol_type: str = "symbol") -> dict:
    return {
        "accountId": act["accountId"],
        "date": act["date"][:18],
        "fee": abs(float(act["fee"])),
        "quantity": abs(float(act["quantity"])),
        "symbol": act.get(symbol_type, ""),
        "type": act["type"],
        "unitPrice": act["unitPrice"]
    }


def is_act_present(new_act, existing_acts, synced_acts_ids: set):
    comment = new_act.get("comment")
    if comment:
        match = re.search(r"tradeID=(\d+)", comment)
        if match and match.group(1) in synced_acts_ids:
            return True
    # Compare only using the "symbol" field.
    for existing_act in existing_acts:
        if format_existing_act(existing_act, "symbol") == format_new_act(new_act, "symbol"):
            return True
    return False


def get_diff(old_acts, new_acts):
    diff = []
    synced_acts_ids = set()
    for old_act in old_acts:
        comment = old_act.get("comment")
        if comment:
            match = re.search(r"tradeID=(\d+)", comment)
            if match:
                synced_acts_ids.add(match.group(1))
    for new_act in new_acts:
        if not is_act_present(new_act, old_acts, synced_acts_ids):
            # Remove extra property not allowed by Ghostfolio.
            new_act.pop("binanceSymbol", None)
            diff.append(new_act)
    return diff


class SyncBinance:
    def __init__(self, ghost_host, ghost_key, ghost_token, ghost_account_name,
                 ghost_currency, ghost_platform, binance_api_key, binance_api_secret, binance_symbols=None):
        if ghost_token == "" and ghost_key:
            self.ghost_token = self.create_ghost_token(ghost_host, ghost_key)
        else:
            self.ghost_token = ghost_token
        if not self.ghost_token:
            logger.info("No bearer token provided, closing now")
            raise Exception("No bearer token provided")
        self.ghost_host = ghost_host
        self.ghost_account_name = ghost_account_name
        self.ghost_currency = ghost_currency  # e.g. "USDT"
        self.ghost_platform = ghost_platform
        self.binance_api_key = binance_api_key
        self.binance_api_secret = binance_api_secret
        # Optional list of symbols; if not provided, the script will derive symbols from account balances.
        self.binance_symbols = binance_symbols if binance_symbols is not None else []
        self.symbol_mapping = {}  # We assume symbols match on both platforms.
        self.account_id: Optional[str] = None

    def create_ghost_token(self, ghost_host, ghost_key):
        token = {'accessToken': ghost_key}
        url = f"{ghost_host}/api/v1/auth/anonymous"
        payload = json.dumps(token)
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return ""
        if response.status_code == 201:
            return response.json().get("authToken", "")
        return ""

    def sign_params(self, params: dict) -> dict:
        params['timestamp'] = int(time.time() * 1000)
        query_string = '&'.join(f"{k}={params[k]}" for k in sorted(params))
        signature = hmac.new(self.binance_api_secret.encode('utf-8'),
                             query_string.encode('utf-8'),
                             hashlib.sha256).hexdigest()
        params['signature'] = signature
        return params

    def get_binance_account_info(self):
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/account"
        params = {}
        signed_params = self.sign_params(params)
        headers = {'X-MBX-APIKEY': self.binance_api_key}
        try:
            response = requests.get(base_url + endpoint, headers=headers, params=signed_params)
        except Exception as e:
            logger.info(e)
            return None
        if response.status_code == 200:
            return response.json()
        logger.info("Failed to get Binance account info: %s", response.text)
        return None

    def get_cash_amount_from_binance(self, account_info):
        for balance in account_info.get("balances", []):
            if balance.get("asset") == self.ghost_currency:
                try:
                    return {self.ghost_currency: float(balance.get("free", "0"))}
                except Exception as e:
                    logger.info(e)
        return {}

    def derive_symbols_from_account(self, account_info):
        """
        Derive trading pairs from account balances.
        Assumes that for each asset (except the base/quote currency),
        the trading pair is asset+ghost_currency.
        """
        symbols = []
        for balance in account_info.get("balances", []):
            asset = balance.get("asset")
            if asset and asset != self.ghost_currency:
                symbol = asset + self.ghost_currency
                symbols.append(symbol)
        return symbols

    def get_binance_trades(self):
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/myTrades"
        all_trades = []
        headers = {'X-MBX-APIKEY': self.binance_api_key}

        # If no symbols were provided, derive them from account info.
        if not self.binance_symbols:
            account_info = self.get_binance_account_info()
            if account_info is None:
                logger.info("Cannot derive symbols: no account info")
                return []
            self.binance_symbols = self.derive_symbols_from_account(account_info)
            logger.info("Derived trading symbols: %s", self.binance_symbols)

        for symbol in self.binance_symbols:
            params = {"symbol": symbol}
            signed_params = self.sign_params(params)
            try:
                response = requests.get(base_url + endpoint, headers=headers, params=signed_params)
            except Exception as e:
                logger.info(e)
                continue
            if response.status_code == 200:
                trades = response.json()
                for trade in trades:
                    trade_time = datetime.fromtimestamp(trade["time"] / 1000).isoformat()
                    # Since we're assuming symbols match, no extra mapping is needed.
                    mapped_symbol = symbol
                    trade_type = "BUY" if trade.get("isBuyer", False) else "SELL"
                    act = {
                        "accountId": self.create_or_get_binance_accountId(),
                        "comment": f"tradeID={trade['id']}",
                        "currency": self.ghost_currency,
                        "date": trade_time,
                        "fee": abs(float(trade.get("commission", "0"))),
                        "quantity": abs(float(trade.get("qty", "0"))),
                        "symbol": mapped_symbol.replace("USDT", "USD"), # TODO This should use a map of symbols instead of this
                        "type": trade_type,
                        "unitPrice": float(trade.get("price", "0")),
                        "binanceSymbol": symbol
                    }
                    all_trades.append(act)
            else:
                logger.info("Failed to get trades for symbol %s: %s", symbol, response.text)
        return all_trades

    def set_cash_to_account(self, account_id, cash: dict):
        if not cash:
            logger.info("No cash retrieved")
            return False
        for currency, amount in cash.items():
            payload_data = {
                "balance": amount,
                "id": account_id,
                "currency": currency,
                "isExcluded": False,
                "name": self.ghost_account_name,
                "platformId": self.ghost_platform
            }
            url = f"{self.ghost_host}/api/v1/account/{account_id}"
            payload = json.dumps(payload_data)
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }
            try:
                response = requests.put(url, headers=headers, data=payload)
            except Exception as e:
                logger.info(e)
                return
            if response.status_code == 200:
                logger.info("Updated cash for account %s", account_id)
            else:
                logger.info("Failed to update cash: %s", response.text)

    def create_binance_account(self):
        payload_data = {
            "balance": 0,
            "currency": self.ghost_currency,
            "isExcluded": False,
            "name": self.ghost_account_name,
            "platformId": self.ghost_platform
        }
        url = f"{self.ghost_host}/api/v1/account"
        payload = json.dumps(payload_data)
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(url, headers=headers, data=payload)
        except Exception as e:
            logger.info(e)
            return ""
        if response.status_code == 201:
            return response.json().get("id", "")
        logger.info("Failed to create account: %s", response.text)
        return ""

    def get_all_accounts(self):
        url = f"{self.ghost_host}/api/v1/account"
        headers = {'Authorization': f"Bearer {self.ghost_token}"}
        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            logger.info(e)
            return []
        if response.status_code == 200:
            return response.json().get("accounts", [])
        return []

    def create_or_get_binance_accountId(self):
        if self.account_id is not None:
            return self.account_id
        accounts = self.get_all_accounts()
        for account in accounts:
            if account.get("name") == self.ghost_account_name:
                self.account_id = account.get("id")
                return self.account_id
        self.account_id = self.create_binance_account()
        return self.account_id

    def import_act(self, bulk):
        chunks = generate_chunks(sorted(bulk, key=lambda x: x["date"]), 10)
        for acts in chunks:
            url = f"{self.ghost_host}/api/v1/import"
            payload = json.dumps({"activities": acts})
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }
            logger.info(payload)
            try:
                response = requests.post(url, headers=headers, data=payload)
            except Exception as e:
                logger.info(e)
                return False
            if response.status_code == 201:
                logger.info("Imported activities: %s", json.dumps(response.json()))
            else:
                logger.info("Failed to import activities: %s", response.text)
                return False
        return True

    def get_all_acts_for_account(self, account_id: str = None, range: str = None, symbol: str = None):
        if account_id is None:
            account_id = self.create_or_get_binance_accountId()
        url = f"{self.ghost_host}/api/v1/order"
        params = {"accounts": account_id, "range": range, "symbol": symbol}
        headers = {'Authorization': f"Bearer {self.ghost_token}"}
        try:
            response = requests.get(url, headers=headers, params=params)
        except Exception as e:
            logger.info(e)
            return []
        if response.status_code == 200:
            return response.json().get("activities", [])
        return []

    def sync_binance(self):
        account_info = self.get_binance_account_info()
        if account_info is None:
            logger.info("No account info retrieved from Binance")
            return
        cash = self.get_cash_amount_from_binance(account_info)
        account_id = self.create_or_get_binance_accountId()
        if not account_id:
            logger.info("Failed to retrieve account ID")
            return
        self.set_cash_to_account(account_id, cash)
        trades = self.get_binance_trades()
        existing_acts = self.get_all_acts_for_account()
        diff = get_diff(existing_acts, trades)
        if not diff:
            logger.info("No new trades to sync")
        else:
            self.import_act(diff)


def main():
    # Ghostfolio parameters
    ghost_host = "https://ghostfol.io/"
    ghost_key = ""
    ghost_token = ""  # Leave empty to fetch one using ghost_key
    ghost_account_name = "Binance Account"
    ghost_currency = "USD"
    # This is for coinbase so the icon is going to be wrong
    ghost_platform = "8dc24b88-bb92-4152-af25-fe6a31643e26"

    # Binance API parameters
    binance_api_key = ""
    binance_api_secret = ""
    # Provide a list of symbols to sync; assume symbols match on both platforms.
    # TODO ADD SYMBOLS, MAYBE TURN THIS INTO A MAPPING FILE, if too many symbols this is going to take a while
    binance_symbols = ["BTCUSDT", "ETHUSDT", "USDCUSDT", "BNBUSDT"]

    sync = SyncBinance(
        ghost_host=ghost_host,
        ghost_key=ghost_key,
        ghost_token=ghost_token,
        ghost_account_name=ghost_account_name,
        ghost_currency=ghost_currency,
        ghost_platform=ghost_platform,
        binance_api_key=binance_api_key,
        binance_api_secret=binance_api_secret,
        binance_symbols=binance_symbols
    )

    sync.sync_binance()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
