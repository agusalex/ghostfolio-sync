import json
from collections import namedtuple

import requests
import sys

from cachetools import TTLCache, cached

import LoggerFactory

SymbolLookupOverride = namedtuple('SymbolLookupOverride',
                                  'exists data_source symbol currency')
GhostfolioConfig = namedtuple('GhostfolioConfig',
                              'token host currency account_name, '
                              'platform_id platform_name')
GhostfolioTicker = namedtuple('GhostfolioTicker',
                              'data_source, symbol, currency')
GhostfolioImportActivity = namedtuple('GhostfolioImportActivity',
                                      'currency, dataSource, date, fee, quantity, '
                                      'symbol, type, unitPrice, account_id, comment')

DATA_SOURCE_YAHOO = "YAHOO"

cache = TTLCache(maxsize=100, ttl=300)
logger = LoggerFactory.logger


class GhostfolioApi:

    def __init__(self, config: GhostfolioConfig):
        self.ghost_token = config.token
        self.ghost_host = config.host
        self.ghost_currency = config.currency
        self.ghost_account_sync_name = config.account_name
        self.ibkr_platform_name = config.platform_name
        self.account_name = config.account_name
        # todo should not do magic in ctor...
        if config.platform_id is None:
            self.ibkr_platform_id = self.__get_ibkr_platform_id()
        else:
            self.ibkr_platform_id = config.platform_id

    def update_account(self, account_id, account):
        url = f"{self.ghost_host}/api/v1/account/{account_id}"

        payload = json.dumps(account)
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
            'Content-Type': 'application/json'
        }
        try:
            self.__log_request(url, account)
            response = requests.request("PUT", url, headers=headers, data=payload)
        except Exception as e:
            self.__log_request_error(url, f"{e}")
            return False
        if response.status_code == 200:
            self.__log_request(url, f"Updated Cash for account {response.json()['id']}")
        else:
            self.__log_request_error(url, f"Failed create: {response.text}")
        return response.status_code == 200

    def delete_activity(self, act_id):
        url = f"{self.ghost_host}/api/v1/order/{act_id}"

        payload = {}
        headers = self.__get_header_with_ghostfolio_auth()
        try:
            self.__log_request(url)
            response = requests.request("DELETE", url, headers=headers, data=payload)
        except Exception as e:
            self.__log_request_error(url, e)
            return False

        return response.status_code == 200

    @staticmethod
    def validate_and_convert_response_to_assets(response):
        if response.status_code == 200:
            items = response.json().get('items')
            if len(items) > 1:
                # inform fuzzy match, but still do it :D
                logger.info("fuzzy match to first symbol for %s in %s",
                            response.request.url,
                            items)
            if len(items) >= 1:
                return True, items[0]
            return False, None
        else:
            raise Exception(response)

    def get_all_activities(self) -> list[GhostfolioImportActivity]:
        url = f"{self.ghost_host}/api/v1/order"

        payload = {}
        headers = self.__get_header_with_ghostfolio_auth()
        try:
            self.__log_request(url)
            response = requests.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            logger.warning(
                f"get_all_activities {url} error while fetching all activities: {e}"
            )
            return []

        if response.status_code == 200:
            activities = response.json()['activities']
            self.__log_request(url, f"received {len(activities)} activities")
            import_activities: list[GhostfolioImportActivity] = []
            for activity in activities:
                import_activities.append(self.map_activity_to_import_activity(activity))
            return import_activities
        else:
            return []

    def import_activities(self, bulk):
        chunks = self.__generate_chunks(bulk, 10)
        for acts in chunks:
            url = f"{self.ghost_host}/api/v1/import"
            formatted_acts = json.dumps(
                {"activities": sorted(acts, key=lambda x: x["date"])}
            )
            payload = formatted_acts
            headers = {
                'Authorization': f"Bearer {self.ghost_token}",
                'Content-Type': 'application/json'
            }
            logger.info("import_activities Adding activities: \n" + formatted_acts)
            try:
                logger.debug(
                    f"import_activities {url} adding {len(formatted_acts)} activities"
                )
                self.__log_request(url, f"adding {len(formatted_acts)} activities")
                response = requests.request("POST", url, headers=headers, data=payload)
            except Exception as e:
                logger.warning(f"import_activities {url} exception; {e}")
                self.__log_request_error(
                    url,
                    f"with payload: {payload} failed with {e}"
                )
                return False
            if response.status_code == 201:
                logger.info(
                    f"import_activities {url} created {len(formatted_acts)} activities"
                )
            else:
                message = f"Failed create following activities:" \
                          f" {formatted_acts}: {response.text}"
                self.__log_request_error(url, message)
            if response.status_code != 201:
                return False
        return True

    def add_activity(self, act):
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
            logger.error(e)
            return False
        if response.status_code == 201:
            self.__log_request(url, f"created {response.json()['id']}")
        else:
            self.__log_request_error(url, f"Failed create: {response.text}")
        return response.status_code == 201

    def create_or_get_ibkr_account(self):
        accounts = self.get_ghostfolio_accounts()
        for account in accounts:
            if account["name"] == self.ghost_account_sync_name:
                return account
        return self.__create_ibkr_account()

    def __create_ibkr_account(self):
        account = {
            "accountType": "SECURITIES",
            "balance": 0,
            "currency": self.ghost_currency,
            "isExcluded": False,
            "name": self.ghost_account_sync_name,
            "platformId": self.ibkr_platform_id,
        }
        return self.create_account(account)

    def delete_all_activities(self, account_id):
        acts: list[GhostfolioImportActivity] = self.get_all_activities_for_account(
            account_id
        )

        if not acts:
            logger.info("No activities to delete")
            return True
        complete = True

        for act in acts:
            if act.account_id == account_id:
                act_complete = self.delete_activity(act.account_id)
                complete = complete and act_complete
                if act_complete:
                    logger.info("Deleted: %s", act.account_id)
                else:
                    logger.warning("Failed Delete: %s", act.account_id)
        return complete

    def get_all_activities_for_account(
            self,
            account_id: str
    ) -> list[GhostfolioImportActivity]:
        acts: list[GhostfolioImportActivity] = self.get_all_activities()
        filtered_acts: list[GhostfolioImportActivity] = []
        for act in acts:
            if act.account_id == account_id:
                filtered_acts.append(act)
        return filtered_acts

    def map_activity_to_import_activity(self, act) -> GhostfolioImportActivity:
        symbol_profile = act['SymbolProfile']
        import_activity = GhostfolioImportActivity(
            symbol_profile['currency'],
            symbol_profile['dataSource'],
            act['date'],
            act['fee'],
            act['quantity'],
            symbol_profile['symbol'],
            act['type'],
            act['unitPrice'],
            act['accountId'],
            act['comment'],
        )
        return import_activity

    def create_account(self, account):
        url = f"{self.ghost_host}/api/v1/account"

        payload = json.dumps(account)
        headers = {
            'Authorization': f"Bearer {self.ghost_token}",
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            print(e)
            return ""
        if response.status_code == 201:
            return response.json()["id"]
        logger.warning(f"create_account: Failed creating {url}: {account}")
        return ""

    def get_ghostfolio_accounts(self):
        url = f"{self.ghost_host}/api/v1/account"

        payload = {}
        headers = self.__get_header_with_ghostfolio_auth()
        try:
            self.__log_request(url)
            response = requests.request("GET", url, headers=headers, data=payload)
        except Exception as e:
            logger.error(e)
            return []
        if response.status_code == 200:
            return response.json()['accounts']
        else:
            raise Exception(response)

    @cached(cache)
    def get_ticker(self, isin, symbol) -> GhostfolioTicker:
        override: SymbolLookupOverride = self.__lookup_overrides(isin, symbol)
        if override.exists:
            return GhostfolioTicker(
                override.data_source,
                override.symbol,
                override.currency
            )
        # for now only yahoo
        data_source = DATA_SOURCE_YAHOO
        successful, ticker = self.__lookup_asset(isin)
        if not successful:
            successful, ticker = self.__lookup_asset(symbol)
            if not successful:
                raise Exception(f"no symbol found for {isin} {symbol}")
        return GhostfolioTicker(
            data_source,
            ticker.get('symbol'),
            ticker.get('currency')
        )

    def __lookup_asset(self, query):
        url = f"{self.ghost_host}/api/v1/symbol/lookup?query={query}"
        headers = self.__get_header_with_ghostfolio_auth()
        try:
            self.__log_request(url)
            response = requests.request("GET", url, headers=headers)
            return self.validate_and_convert_response_to_assets(response)
        except Exception as e:
            self.__log_request_error(url, f"lookup asset: {query} failed with {e}")
            return False, None

    @staticmethod
    def __generate_chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def __get_header_with_ghostfolio_auth(self):
        return {
            'Authorization': f"Bearer {self.ghost_token}",
        }

    def __log_request(self, url, message="no-message"):
        previous_function_name = sys._getframe(1).f_code.co_name
        logger.debug(f"{previous_function_name} {url}: {message}")

    def __log_request_error(self, url, message="no-message"):
        previous_function_name = sys._getframe(1).f_code.co_name
        logger.error(f"{previous_function_name} {url}: {message}")

    def __lookup_overrides(self, isin, symbol) -> SymbolLookupOverride:
        # TODO create a way to lookup stuff
        return SymbolLookupOverride(False, None, None, None)

    def __get_ibkr_platform_id(self):
        url = f"{self.ghost_host}/api/v1/info"
        headers = self.__get_header_with_ghostfolio_auth()
        try:
            self.__log_request(url)
            response = requests.request("GET", url, headers=headers)
            for platform in response.json()['platforms']:
                if platform['name'] == self.ibkr_platform_name:
                    return platform['id']
            raise Exception(f"no platform found for name {self.ibkr_platform_name} "
                            f"in {response.json()['platforms']}")
        except Exception as e:
            self.__log_request_error(url, f"lookup failed with {e}")
            return None
