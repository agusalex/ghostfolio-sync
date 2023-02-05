from time import sleep

import requests
from ibflex import client, parser, FlexQueryResponse, BuySell
from datetime import datetime
import os
import json

IBKRCATEGORY = "9da3a8a7-4795-43e3-a6db-ccb914189737"

SYNCIBKR = "SYNCIBKR"

DELETEALL = "DELETEALL"

ghost_token = os.environ.get('GHOST_TOKEN')
ibkrtoken = os.environ.get("IBKR-TOKEN")
ibkrquery = os.environ.get("IBKR-QUERY")
default_host = "https://ghostfol.io"
ghost_host = os.environ.get("GHOST_HOST", default_host)
yahoo_source = "5941484f4f" if ghost_host == default_host else "YAHOO"
operation = os.environ.get("OPERATION", SYNCIBKR)


def sync_ibkr():
    print("Fetching Query")
    response = client.download(ibkrtoken, ibkrquery)
    print("Parsing Query")
    query: FlexQueryResponse = parser.parse(response)
    activities = []
    date_format = "%Y-%m-%d"
    account_id = createOrGetIBKRAccountID()
    if account_id == "":
        print("Failed to retrieve account ID closing now")
        return
    setCashToAccount(account_id, query)
    for trade in query.FlexStatements[0].Trades:
        if trade.openCloseIndicator.CLOSE:
            date = datetime.strptime(str(trade.tradeDate), date_format)
            iso_format = date.isoformat()
            symbol = trade.symbol
            if ".USD-PAXOS" in trade.symbol:
                symbol = trade.symbol.replace(".USD-PAXOS", "") + "USD"

            if trade.buySell == BuySell.BUY:
                buysell = "BUY"
            else:
                buysell = "SELL"

            activities.append({
                "accountId": account_id,
                "currency": trade.currency,
                "dataSource": yahoo_source,
                "date": iso_format,
                "fee": float(0),
                "quantity": abs(float(trade.quantity)),
                "symbol": symbol,
                "type": buysell,
                "unitPrice": float(trade.tradePrice)
            })

    for activity in sorted(activities, key=lambda x: x["date"]):
        addAct(activity)
        sleep(3)


def getCashAmmountFromFlex(query):
    cash = 0
    try:
        cash += query.FlexStatements[0].CashReport[0].endingCash
    except Exception as e:
        print(e)
    try:
        cash += query.FlexStatements[0].CashReport[0].endingCashPaxos
    except Exception as e:
        print(e)
    return cash


def setCashToAccount(account_id, query):
    cash = getCashAmmountFromFlex(query)
    if cash == 0:
        print("No cash set, no cash retrieved")
        return False
    account = {"accountType": "SECURITIES", "balance": float(cash), "id": account_id, "currency": "USD",
               "isExcluded": False,
               "name": "IBKR",
               "platformId": IBKRCATEGORY}

    url = f"{ghost_host}/api/v1/account/{account_id}"

    payload = json.dumps(account)
    headers = {
        'Authorization': f"Bearer {ghost_token}",
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request("PUT", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
        return False
    if response.status_code == 200:
        print(f"created {response.json()['id']}")
    else:
        print("Failed create: " + response.text)
    return response.status_code == 200


def deleteAct(act_id):
    url = f"{ghost_host}/api/v1/order/{act_id}"

    payload = {}
    headers = {
        'Authorization': f"Bearer {ghost_token}",
    }
    try:
        response = requests.request("DELETE", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
        return False

    return response.status_code == 200


def addAct(act):
    url = f"{ghost_host}/api/v1/order"

    payload = json.dumps(act)
    headers = {
        'Authorization': f"Bearer {ghost_token}",
        'Content-Type': 'application/json'
    }
    print("Adding activity: " + json.dumps(act))
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
        return False
    if response.status_code == 201:
        print(f"created {response.json()['id']}")
    else:
        print("Failed create: " + response.text)
    return response.status_code == 201


def createIBKRAccount():
    account = {"accountType": "SECURITIES", "balance": 0, "currency": "USD", "isExcluded": False, "name": "IBKR",
               "platformId": "9da3a8a7-4795-43e3-a6db-ccb914189737"}

    url = f"{ghost_host}/api/v1/account"

    payload = json.dumps(account)
    headers = {
        'Authorization': f"Bearer {ghost_token}",
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
        return ""
    if response.status_code == 201:
        return response.json()["id"]
    print("Failed creating ")
    return ""


def getAccounts():
    url = f"{ghost_host}/api/v1/account"

    payload = {}
    headers = {
        'Authorization': f"Bearer {ghost_token}",
    }
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
        return []

    return response.json()['accounts']


def createOrGetIBKRAccountID():
    accounts = getAccounts()
    for account in accounts:
        if account["name"] == "IBKR":
            return account["id"]
    return createIBKRAccount()


def deleteAllActs():
    acts = getAllActs()
    if not acts:
        print("No activities to delete")
        return True
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
    url = f"{ghost_host}/api/v1/order"

    payload = {}
    headers = {
        'Authorization': f"Bearer {ghost_token}",
    }
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
        return []

    if response.status_code == 200:
        return response.json()['activities']
    else:
        return []


if __name__ == '__main__':
    if operation == SYNCIBKR:
        print("Starting sync")
        sync_ibkr()
        print("End sync")
    elif operation == DELETEALL:
        print("Starting delete")
        deleteAllActs()
        print("End delete")
    else:
        print("Unknown Operation")
