# Ghostfolio-Sync

[![Docker Hub package][dockerhub-badge]][dockerhub-link]

[dockerhub-badge]: https://img.shields.io/badge/images%20on-Docker%20Hub-blue.svg
[dockerhub-link]: https://hub.docker.com/repository/docker/agusalex/ghostfolio-sync "Docker Hub Image"

Sync your Ghostfolio with IBKR 
( more to come? Help is always welcome! )

## Setup

### IBKR
**Important**:  When you configure your Flex Query give it: **Cash report** and **Cash transactions** and **Trades** and nothing else

Follow this guide to configure your Flex Queries in your Interactive Brokers account:
https://help.wealthica.com/help/how-to-connect-ib-interactive-brokers-and-configure-the-flex-report



**Important: If you dont want ghostfolio-sync to sync everything everytime and make it quicker, just set a shorter window for the query. Keep in mind that what was not synced by ghostfolio-sync in that period of time will be lost (ie when the window moves and content was not uploaded to ghostfolio). This can be avoided at the cost of a longer window of time and longer sync**

### Ghostfolio
* Take note of your user **KEY** (generated upon user creation and used to login to Ghostfolio)
* Run the following on the terminal (replace `ghostfol.io` with `localhost` or your host url if you are self-hosting):

```
curl -X POST -H "Content-Type: application/json" \
	-d '{ "accessToken": "YOUR-USER-KEY-GOES-HERE }' \    
	https://ghostfol.io/api/v1/auth/anonymous
```

* Take note of the token `{"authToken":"12cd45...`. That is your **GHOST_TOKEN**

## Run in Docker

```docker run -e GHOST_TOKEN=YOUR_GHOST_TOKEN -e IBKR_TOKEN=YOUR-IBKR-TOKEN -e IBKR_QUERY=YOUR-IBKR-QUERY agusalex/ghostfolio-sync```

### More Options
| Envs |Description  |
|--|--|
|**IBKR_TOKEN**  | Your Token  |
|**IBKR_QUERY**  | Your Query ID |
|**GHOST_TOKEN**  | The token for your ghostfolio account |
|**GHOST_HOST**  | (optional) Ghostfolio Host, only add if using custom ghostfolio |
|**GHOST_CURRENCY**  | (optional) Ghostfolio Account Currency, only applied if account doesn't exist |
|**CRON**  | (optional) To run on a [Cron Schedule](https://crontab.guru/) |
|**OPERATION** | (optional) SYNCIBKR (default) or DELETEALL (will erase all operations of all accounts) |

## Contributing

* Feel free to submit any issue or PR's you think necessary
* If you like the work and want to buy me a coffee you are more than welcome :)

<a href="https://www.buymeacoffee.com/YiQkYsghUQ" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
