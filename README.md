# Ghostfolio-Sync

[![Docker Hub package][dockerhub-badge]][dockerhub-link]

[dockerhub-badge]: https://img.shields.io/badge/images%20on-Docker%20Hub-blue.svg
[dockerhub-link]: https://hub.docker.com/repository/docker/agusalex/ghostfolio-sync "Docker Hub Image"

Sync your Ghostfolio with IBKR 
( more to come? Help is always welcome! )

## Setup

### IBKR
**Important**:  When you configure your Flex Query give it:
* Account Information: Currency
* Cash Report: Currency, Ending Cash
* Trades: Select All (however there is a risk new IBKR fields will cause issues)

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

```docker run -e IBKR_ACCOUNT_ID=$IBKR_ACCOUNT_ID -e GHOST_TOKEN=YOUR_GHOST_TOKEN -e IBKR_TOKEN=YOUR-IBKR-TOKEN -e IBKR_QUERY=YOUR-IBKR-QUERY agusalex/ghostfolio-sync```

In Podman

```podman run -e IBKR_ACCOUNT_ID=$IBKR_ACCOUNT_ID -e GHOST_TOKEN=YOUR_GHOST_TOKEN -e IBKR_TOKEN=$IBKR_TOKEN -e IBKR_QUERY=$IBKR_QUERY -e GHOST_HOST=http://$GHOST_URL -e GHOST_CURRENCY=EUR -e GHOST_IBKR_PLATFORM=$IBKR_PLATFORM -v ./mapping.yaml:/usr/app/src/mapping.yaml:Z agusalex/ghostfolio-sync```

### Symbol mapping

You can specify the symbol mappings in `mapping.yaml` and you do not need to rebuild the container with the above mount command.


### More Options
| Envs | Mutiple ( Comma-separated ) | Description  |
|--|--|--|
|**IBKR_ACCOUNT_ID**  |Yes| Your IBKR Account ID  |
|**IBKR_TOKEN**   |Yes| Your Token  |
|**IBKR_QUERY**   |Yes| Your Query ID |
|**GHOST_TOKEN**   |Yes| The token for your ghostfolio account |
|**GHOST_KEY**   |Yes| The key for your ghostfolio account, if this is used you don't need **GHOST_TOKEN** and vice-versa |
|**GHOST_HOST**   |Yes| (optional) Ghostfolio Host, only add if using custom ghostfolio |
|**GHOST_CURRENCY**   |Yes| (optional) Ghostfolio Account Currency, only applied if the account doesn't exist |
|**GHOST_IBKR_PLATFORM**  |Yes| (optional) For self-hosted, specify the Platform ID |
|**CRON**  |Yes| (optional) To run on a [Cron Schedule](https://crontab.guru/) |
|**OPERATION**  |Yes| (optional) SYNCIBKR (default) or DELETEALL (will erase all operations of all accounts) |

### Configuring / Retrieving Platform ID

If you are using ghostfolio self-hosted option, you need to go into Ghostfolio and add a platform for IBKR.

Then make a request to `/account` to find the relevant platform ID and store it in the IBKR_PLATFORM env variable

```bash
curl "http://10.0.0.2:3333/api/v1/account" \
     -H "Authorization: Bearer $GHOST_TOKEN"

export IBKR_PLATFORM=<PUT PLATFORM ID HERE>
```

## Contributing

* Feel free to submit any issue or PR's you think necessary
* If you like the work and want to buy me a coffee you are more than welcome :)

<a href="https://www.buymeacoffee.com/YiQkYsghUQ" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
