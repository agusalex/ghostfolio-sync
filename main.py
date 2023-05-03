import os
import LoggerFactory
from SyncIBKR import SyncIBKR

SYNCIBKR = "SYNCIBKR"

DELETEALL = "DELETEALL"

GETALLACTS = "GETALLACTS"

ghost_tokens = os.environ.get('GHOST_TOKEN').split(",")
ibkr_tokens = os.environ.get("IBKR_TOKEN").split(",")
ibkr_queries = os.environ.get("IBKR_QUERY").split(",")
ghost_hosts = os.environ.get("GHOST_HOST", "https://ghostfol.io").split(",")
ghost_currency = os.environ.get("GHOST_CURRENCY", "USD").split(",")
operations = os.environ.get("OPERATION", SYNCIBKR).split(",")

logger = LoggerFactory.logger

if __name__ == '__main__':
    for i in range(len(operations)):
        ghost = SyncIBKR(
            ghost_hosts[i],
            ibkr_tokens[i],
            ibkr_queries[i],
            ghost_tokens[i],
            ghost_currency[i]
        )
        if operations[i] == SYNCIBKR:
            logger.info("Starting sync")
            ghost.sync_ibkr()
            logger.info("End sync")
        elif operations[i] == DELETEALL:
            logger.info("Starting delete")
            ghost.delete_all_activities()
            logger.info("End delete")
        else:
            logger.warning("Unknown Operation")
