from narraint.queryengine.result import QueryDocumentResult


class QueryResultAggregationStrategy:
    """
    Base for all ranking strategies
    A strategy must rank a list of document results
    """
    def rank_results(self, results: [QueryDocumentResult]):
        raise NotImplementedError
