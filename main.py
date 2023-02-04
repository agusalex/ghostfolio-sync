from ibflex import client, parser, FlexQueryResponse, Trade
from datetime import datetime
import os

def get_trades():
    ibkrtoken = os.environ.get("IBKR-TOKEN")
    ibkrquery = os.environ.get("IBKR-QUERY")
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

            activities.append({
                "accountId": "426f6dff-d019-4662-a92c-7f14b08a3235",
                "currency": trade.currency,
                "dataSource": "YAHOO",
                "date": iso_format,
                "fee": float(0),
                "quantity": float(trade.quantity),
                "symbol": symbol,
                "type": trade.buySell,
                "unitPrice": float(trade.tradePrice)
            })
    activities = {"activities": sorted(activities, key=lambda x: x["date"])}
    return activities
