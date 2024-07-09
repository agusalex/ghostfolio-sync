import os
from SyncIBKR import SyncIBKR

SYNCIBKR = "SYNCIBKR"

DELETEALL = "DELETEALL"

GETALLACTS = "GETALLACTS"

ghost_keys = os.environ.get("GHOST_KEY", "").split(",")
ghost_tokens = os.environ.get('GHOST_TOKEN', "").split(",")
ibkr_tokens = os.environ.get("IBKR_TOKEN").split(",")
ibkr_queries = os.environ.get("IBKR_QUERY").split(",")
ghost_hosts = os.environ.get("GHOST_HOST", "https://ghostfol.io").split(",")
ghost_currency = os.environ.get("GHOST_CURRENCY", "USD").split(",")
operations = os.environ.get("OPERATION", SYNCIBKR).split(",")
ghost_ibkr_platform = os.environ.get("GHOST_IBKR_PLATFORM", "66b22c82-a96c-4e4f-aaf2-64b4ca41dda2").split(",")

if __name__ == '__main__':
    for i in range(len(operations)):
        ghost = SyncIBKR(ghost_hosts[i], ibkr_tokens[i], ibkr_queries[i], ghost_keys[i], ghost_tokens[i], ghost_currency[i], ghost_ibkr_platform[i])
        if operations[i] == SYNCIBKR:
            print("Starting sync")
            ghost.sync_ibkr()
            print("End sync")
        elif operations[i] == DELETEALL:
            print("Starting delete")
            ghost.delete_all_acts()
            print("End delete")
        else:
            print("Unknown Operation")
