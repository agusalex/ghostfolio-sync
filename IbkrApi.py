from collections import namedtuple
from datetime import datetime

from diskcache import Cache
from ibflex import client, parser, FlexQueryResponse, CashAction, CashTransaction, Trade

import LoggerFactory
from EnvironmentConfiguration import EnvironmentConfiguration

IbkrConfig = namedtuple('IbkrConfig',
                        'token query_id')

logger = LoggerFactory.logger
cache = Cache(directory='.cache/ibkr-api')
envConf = EnvironmentConfiguration()


class IbkrApi():

    def __init__(self, ibkr_config: IbkrConfig):
        self.ibkr_token = ibkr_config.token
        self.ibkr_query = ibkr_config.query_id

    @cache.memoize(expire=3600, tag='query')
    def get_and_parse_query(self):
        logger.debug("Fetching Query")
        response = client.download(self.ibkr_token, self.ibkr_query)
        if envConf.is_debug_files_enabled():
            self.__query_to_file(response)
        logger.debug("Parsing Query")
        query: FlexQueryResponse = parser.parse(response)
        return query

    @staticmethod
    def get_stock_transactions(query: FlexQueryResponse) -> list[Trade]:
        skipped_categories_counter = {}
        trades: list[Trade] = []
        for trade in query.FlexStatements[0].Trades:
            if trade.assetCategory is not trade.assetCategory.STOCK:
                logger.debug(f"ignore {trade.assetCategory}, {trade.symbol}: {trade}")
                existing_skips = skipped_categories_counter.get(trade.assetCategory, 0)
                skipped_categories_counter[trade.assetCategory] = existing_skips + 1
                continue

            if trade.openCloseIndicator is None:
                logger.warning("trade is not open or close (ignoring): %s", trade)
                continue

            trades.append(trade)

        if len(skipped_categories_counter) > 0:
            logger.info(f"Skipped: {skipped_categories_counter}")

        return trades

    @staticmethod
    def get_cash_transactions(query) -> list[list[CashTransaction]]:
        cash_action_types: list[CashAction] = [CashAction.DIVIDEND,
                                               CashAction.PAYMENTINLIEU,
                                               CashAction.WHTAX]

        transaction_summaries = filter(
            lambda x: x.levelOfDetail == 'SUMMARY' and (x.type in cash_action_types),
            query.FlexStatements[0].CashTransactions
        )
        transaction_sorted = sorted(transaction_summaries, key=lambda t: t.reportDate)
        index = 0
        transaction_chunks: list[list[CashTransaction]] = []
        transaction_group: list[CashTransaction] = []
        while index < len(transaction_sorted):
            actual_element: CashTransaction = transaction_sorted[index]
            next_element_index = index + 1
            if next_element_index >= len(transaction_sorted):
                break
            next_element: CashTransaction = transaction_sorted[next_element_index]
            if len(transaction_group) < 1:
                transaction_chunks.append(transaction_group)
                transaction_group.append(actual_element)
            if actual_element.symbol == next_element.symbol \
                    and actual_element.reportDate == next_element.reportDate:
                transaction_group.append(next_element)
            else:
                transaction_group: list[CashTransaction] = []
            index += 1
        return transaction_chunks

    def __query_to_file(self, response):
        timestamp = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"
        folder = envConf.debug_file_location()
        filename = f"{folder}{timestamp}-ib_flex_query-{self.ibkr_query}.xml"
        logger.warning(f"writing query to {filename}")
        with open(filename, 'wb') as outfile:
            outfile.write(response)
