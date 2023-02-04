import requests
from ibflex import client, parser, FlexQueryResponse, Trade
from datetime import datetime
import os
import json

ghost_token = os.environ.get('GHOST_TOKEN')
ibkrtoken = os.environ.get("IBKR-TOKEN")
ibkrquery = os.environ.get("IBKR-QUERY")
account_id = os.environ.get("GHOST_ACCOUNT", "")
ghost_host = os.environ.get("GHOST_HOST", "https://ghostfol.io")


def sync_ibkr():
    response = client.download(ibkrtoken, ibkrquery)
    query: FlexQueryResponse = parser.parse(response)
    activities = []
    date_format = "%Y-%m-%d"
    for trade in query.FlexStatements[0].Trades:
        if trade.openCloseIndicator.CLOSE:
            date = datetime.strptime(str(trade.tradeDate), date_format)
            iso_format = date.isoformat()
            symbol = trade.symbol
            if ".USD-PAXOS" in trade.symbol:
                symbol = trade.symbol.replace(".USD-PAXOS", "") + "USD"
            if account_id != "":
                activities.append({
                    "accountId": account_id,
                    "currency": trade.currency,
                    "dataSource": "YAHOO",
                    "date": iso_format,
                    "fee": float(0),
                    "quantity": float(trade.quantity),
                    "symbol": symbol,
                    "type": trade.buySell,
                    "unitPrice": float(trade.tradePrice)
                })
            else:
                activities.append({
                    "currency": trade.currency,
                    "dataSource": "YAHOO",
                    "date": iso_format,
                    "fee": float(0),
                    "quantity": float(trade.quantity),
                    "symbol": symbol,
                    "type": trade.buySell,
                    "unitPrice": float(trade.tradePrice)
                })

    for activity in sorted(activities, key=lambda x: x["date"]):
        pushToGhostfolio({"activities": [activity]})


def deleteAct(id):
    url = f"{ghost_host}/api/v1/order/{id}"

    payload = {}
    headers = {
        'Authorization': f"Bearer {ghost_token}",
    }

    response = requests.request("DELETE", url, headers=headers, data=payload)

    return response.status_code == 200


def deleteAllActs():
    acts = getAllActs()
    complete = True
    for act in acts:
        act_complete = deleteAct(act['id'])
        complete = complete and act_complete
        if act_complete:
            print("Deleted: " + act['id'])
        else:
            print("Failed Delete: " + act['id'])
    return complete


def getAllActs():
    url = "https://ghostfol.io/api/v1/order"

    payload = {}
    headers = {
        'Authorization': f"Bearer {ghost_token}",
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    return response.json()['activities']


def pushToGhostfolio(acts):
    url = "https://ghostfol.io/api/v1/import"
    payload = json.dumps(acts)
    headers = {
        'Authorization': f"Bearer {ghost_token}",
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)


if __name__ == '__main__':
    sync_ibkr()