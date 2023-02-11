import os
from SyncIBKR import SyncIBKR

SYNCIBKR = "SYNCIBKR"

DELETEALL = "DELETEALL"

GETALLACTS = "GETALLACTS"

ghost_tokens = os.environ.get('GHOST_TOKEN').split(",")
ibkr_tokens = os.environ.get("IBKR_TOKEN").split(",")
ibkr_queries = os.environ.get("IBKR_QUERY").split(",")
ghost_hosts = os.environ.get("GHOST_HOST", "https://ghostfol.io").split(",")
operations = os.environ.get("OPERATION", SYNCIBKR).split(",")

if __name__ == '__main__':
    for i in range(len(operations)):
        ghost_token = ghost_tokens[i]
        ibkr_token = ibkr_tokens[i]
        ibkr_query = ibkr_queries[i]
        ghost_host = ghost_hosts[i]
        operation = operations[i]
        ghost = SyncIBKR(ghost_host, ibkr_token, ibkr_query, ghost_token)
        if operation == SYNCIBKR:
            print("Starting sync")
            ghost.sync_ibkr()
            print("End sync")
        elif operation == DELETEALL:
            print("Starting delete")
            ghost.delete_all_acts()
            print("End delete")
        else:
            print("Unknown Operation")
