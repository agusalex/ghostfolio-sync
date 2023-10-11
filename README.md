# Ghostfolio-Sync

Sync your (Ghostfolio)[https://ghostfol.io/en/home/overview] with IBKR ( more to come? )

## Kudos 

This is based on [agusalex/ghostfolio-sync](https://github.com/agusalex/ghostfolio-sync) which is a great work.
This fork is more for personal developement, as it runs primarly against a self-hosted instance.

## Setup

### IBKR
Follow this guide to configure your Flex Queries in your Interactive Brokers account:

https://help.wealthica.com/help/how-to-connect-ib-interactive-brokers-and-configure-the-flex-report

When you configure your Flex Query give it, cash statement permissions as well as transaction permisions.

**Important: If you dont want ghostfolio-sync to sync everything everytime and make it quicker, just set a shorter window for the query. Keep in mind that what was not synced by ghostfolio-sync in that period of time will be lost (ie when the window moves and content was not uploaded to ghostfolio). This can be avoided at the cost of a longer window of time and longer sync**

### Ghostfolio
1. Create an account using anonymous option save your **KEY**.
2. Get the **GHOST_TOKEN** for self-hosted `curl -X POST \
   http://192.168.3.1:3333/api/v1/auth/anonymous \
   -H 'Content-Type: application/json' \
   -d '{"accessToken":"REPLACE_WITH_YOUR_KEY"}'`
3. Take note of your **GHOST_TOKEN**

## Run in Docker

Default runs as with the following config (non root):
-  ARG USER=wheel
-  ARG GROUP=default
-  ARG UID=1001
-  ARG GID=1001

Runs with with virtual env

If you need debug files (set WRITE_DEBUG_FILES=TRUE), you can map the default folder /usr/app/src/out

Minimal setup:
``` docker run -e GHOST_TOKEN=YOUR_GHOST_TOKEN -e IBKR_TOKEN=YOUR-IBKR-TOKEN -e IBKR_QUERY=YOUR-IBKR-QUERY```

### More Options
| Envs | Description                                                                                                                              |
|--|------------------------------------------------------------------------------------------------------------------------------------------|
|**CRON**  | (optional) To run on a [Cron Schedule](https://github.com/aptible/supercronic/tree/master/cronexpr#implementation)                       |
|**FILE_WRITE_LOCATION** | (optional) "" (default): write debug files to this folder                                                                                |
|**GHOST_CURRENCY**  | (optional) Ghostfolio Account Currency, only applied if account doesn't exist                                                            |
|**GHOST_HOST**  | (optional) Ghostfolio Host, only add if using custom ghostfolio                                                                          |
|**GHOST_TOKEN**  | The token for your ghostfolio account                                                                                                    |
|**HEALTHCHECK_URL**  | After a successful sync, this url will be accessed                                                                                       |
|**IBKR_QUERY**  | Your Query ID                                                                                                                            |
|**IBKR_TOKEN**  | Your Token                                                                                                                               |
|**LOG_LEVEL** | (optional) INFO (default): standard python (logging levels)[https://docs.python.org/3/library/logging.html#logging-levels] are supported |
|**OPERATION** | (optional) SYNCIBKR (default) or DELETEALL (will erase all operations of all configured accounts)                                        |
|**WRITE_DEBUG_FILES** | (optional) FALSE (default): write debug files                                                                                            |

## Important / Need to know

For identification of synced objects, it will write a field comment on each trade. This looks like `<sync-trade-transactionID>foobar</sync-trade-transactionID>`.
Where foobar is the transactionId from Interactive Brokers.

### symbol lookup 

The symbol lookup is done on ghostfolio. Watch out for messages like: `fuzzy match to first symbol for` this means for the Instrument where multiple results.

### asset classes

Currently, only stocks are supported.  in the log you'll be able to find messages like `DEBUG:SyncIBKR: ignore AssetClass.OPTION: SYMBOL   ID` or `DEBUG:SyncIBKR: ignore AssetClass.CASH: USD.HKD`.
They are summarised in a info statement. For example: `INFO:SyncIBKR: Skipped: {<AssetClass.OPTION: 'OPT'>: 14, <AssetClass.CASH: 'CASH'>: 20}`. May be ghostfolio will support options one day :)

## Contributing

* Feel free to submit any issue or PR's you think necessary
* `pip install ruff` [pretty fast linter](https://github.com/charliermarsh/ruff) to lint
* `pip install pre-commit` [pre-commit](https://pre-commit.com/) to run the linter before commit 
* run-it `ruff check *.py` 