# Ghostfolio-Sync

Sync your Ghostfolio with IBKR ( more to come? )

## Setup

### IBKR
Follow this guide to configure your Flex Queries in your Interactive Brokers account:

https://help.wealthica.com/help/how-to-connect-ib-interactive-brokers-and-configure-the-flex-report

When you configure your Flex Query give it, cash statement permissions as well as transaction permisions.

**Important: If you dont want ghostfolio-sync to sync everything everytime and make it quicker, just set a shorter window for the query. Keep in mind that what was not synced by ghostfolio-sync in that period of time will be lost (ie when the window moves and content was not uploaded to ghostfolio). This can be avoided at the cost of a longer window of time and longer sync**

### Ghostfolio
* Create an account using anonymous option save your **KEY**.
* Go to this link (if using online ghostfolio use https://ghostfol.io) https://**GHOST_HOST**/api/v1/auth/anonymous/**KEY**
* Take note of your **GHOST_TOKEN**

## Run in Docker

``` docker run -e GHOST_TOKEN=YOUR_GHOST_TOKEN -e IBKR_TOKEN=YOUR-IBKR-TOKEN -e IBKR_QUERY=YOUR-IBKR-QUERY```

### More Options
| Envs |Description  |
|--|--|
|**IBKR_TOKEN**  | Your Token  |
|**IBKR_QUERY**  | Your Query ID |
|**GHOST_TOKEN**  | The token for your ghostfolio account |
|**GHOST_HOST**  | (optional) Ghostfolio Host, only add if using custom ghostfolio |
|**CRON**  | (optional) To run on a [Cron Schedule](https://crontab.guru/) |
|**OPERATION** | (optional) SYNCIBKR (default) or DELETEALL (will erase all operations of all accounts) |

<a href="https://www.buymeacoffee.com/YiQkYsghUQ" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
