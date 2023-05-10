from collections import namedtuple
from datetime import datetime

from cachetools import cached, TTLCache
from ibflex import client, parser, FlexQueryResponse

import LoggerFactory
from EnvironmentConfiguration import EnvironmentConfiguration

IbkrConfig = namedtuple('IbkrConfig',
                        'token query_id')

logger = LoggerFactory.logger
cache = TTLCache(maxsize=5, ttl=300)
envConf = EnvironmentConfiguration()


class IbkrApi():
    def __init__(self, ibkrConfig: IbkrConfig):
        self.ibkr_token = ibkrConfig.token
        self.ibkr_query = ibkrConfig.query_id

    @cached(cache)
    def get_and_parse_query(self):
        logger.debug("Fetching Query")
        response = client.download(self.ibkr_token, self.ibkr_query)
        if envConf.is_debug_files_enabled():
            self.__query_to_file(response)
        logger.debug("Parsing Query")
        query: FlexQueryResponse = parser.parse(response)
        return query

    def __query_to_file(self, response):
        timestamp = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"
        folder = envConf.debug_file_location()
        filename = f"{folder}{timestamp}-ib_flex_query-{self.ibkr_query}.xml"
        logger.warning(f"writing query to {filename}")
        with open(filename, 'wb') as outfile:
            outfile.write(response)
