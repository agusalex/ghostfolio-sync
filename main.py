import logging
import os

from SyncIBKR import SyncIBKR
from pretty_print import pretty_print_table

template = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=template)
logger = logging.getLogger(__name__)

SYNCIBKR = "SYNCIBKR"

DELETE_ALL_ACTS = "DELETE_ALL_ACTS"

GET_ALL_ACTS = "GET_ALL_ACTS"

ghost_keys = os.environ.get("GHOST_KEY", "").split(",")
ghost_tokens = os.environ.get("GHOST_TOKEN", "").split(",")
ibkr_tokens = os.environ.get("IBKR_TOKEN", "").split(",")
ibkr_queries = os.environ.get("IBKR_QUERY", "").split(",")
ghost_hosts = os.environ.get("GHOST_HOST", "https://ghostfol.io").split(",")
ibkr_account_ids = os.environ.get("IBKR_ACCOUNT_ID", "").split(",")
ghost_account_names = os.environ.get("GHOST_ACCOUNT_NAME", "Interactive Brokers").split(",")
ghost_currencies = os.environ.get("GHOST_CURRENCY", "USD").split(",")
operations = os.environ.get("OPERATION", SYNCIBKR).split(",")
ghost_ibkr_platforms = os.environ.get("GHOST_IBKR_PLATFORM", "").split(",")


if __name__ == '__main__':
    for i in range(len(operations)):
        ghost_host = ghost_hosts[i] if len(ghost_hosts) > i else ghost_hosts[-1]
        ibkr_token = ibkr_tokens[i] if len(ibkr_tokens) > i else ibkr_tokens[-1]
        ibkr_query = ibkr_queries[i] if len(ibkr_queries) > i else ibkr_queries[-1]
        ghost_key = ghost_keys[i] if len(ghost_keys) > i else ghost_keys[-1]
        ghost_token = ghost_tokens[i] if len(ghost_tokens) > i else ghost_tokens[-1]
        ibkr_account_id = ibkr_account_ids[i] if len(ibkr_account_ids) > i else ibkr_account_ids[-1]
        ghost_account_name = ghost_account_names[i] if len(ghost_account_names) > i else ghost_account_names[-1]
        ghost_currency = ghost_currencies[i] if len(ghost_currencies) > i else ghost_currencies[-1]
        ghost_ibkr_platform = ghost_ibkr_platforms[i] if len(ghost_ibkr_platforms) > i else ghost_ibkr_platforms[-1]

        ghost = SyncIBKR(ghost_host, ibkr_token, ibkr_query, ghost_key, ghost_token, ibkr_account_id,
                         ghost_account_name, ghost_currency, ghost_ibkr_platform)
        if operations[i] == SYNCIBKR:
            logger.info("Starting sync for account %s: %s", i, ibkr_account_ids[i] if len(ibkr_account_ids) > i else "Unknown")
            ghost.sync_ibkr()
            logger.info("End sync")
        elif operations[i] == GET_ALL_ACTS:
            logger.info("Getting all activities")
            logger.info("Start of operation")
            table_data = []
            activities = ghost.get_all_acts_for_account()
            for activity in activities:
                table_data.append([activity['id'], activity['SymbolProfile']['name'], activity['type'],
                                   activity['date'], activity['quantity'], activity['fee'], activity['value'],
                                   activity['SymbolProfile']['currency'], activity['comment']])
            table = pretty_print_table(["ID", "NAME", "TYPE", "DATE", "QUANTITY",
                                        "FEE", "VALUE", "CURRENCY", "COMMENT"],
                                       table_data)
            logger.info("\n%s", table)
            logger.info("End of operation")
        elif operations[i] == DELETE_ALL_ACTS:
            logger.info("Starting delete")
            ghost.delete_all_acts()
            logger.info("End delete")
        else:
            logger.info("Unknown Operation")
