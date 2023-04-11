from ibflex import client, parser, FlexQueryResponse

import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


class IbkrApi():
    def __init__(self, ibkr_token, ibkr_query):
        self.ibkr_token = ibkr_token
        self.ibkr_query = ibkr_query

    def get_and_parse_query(self):
        logger.debug("Fetching Query")
        response = client.download(self.ibkr_token, self.ibkr_query)
        logger.debug("Parsing Query")
        query: FlexQueryResponse = parser.parse(response)
        return query
