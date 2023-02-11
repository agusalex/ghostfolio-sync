import os
from SyncIBKR import SyncIBKR

SYNCIBKR = "SYNCIBKR"

DELETEALL = "DELETEALL"

GETALLACTS = "GETALLACTS"

ghost_token = os.environ.get('GHOST_TOKEN')
ibkrtoken = os.environ.get("IBKR_TOKEN")
ibkrquery = os.environ.get("IBKR_QUERY")
default_host = "https://ghostfolio.expanseailabs.com"
ghost_host = os.environ.get("GHOST_HOST", default_host)
yahoo_source = "YAHOO"
operation = os.environ.get("OPERATION", SYNCIBKR)

if __name__ == '__main__':
    ghost = SyncIBKR(ghost_host, ibkrtoken, ibkrquery, ghost_token)

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
