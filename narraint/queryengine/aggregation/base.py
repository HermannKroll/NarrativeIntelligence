import json
from collections import defaultdict

from narraint.entity.entityresolver import EntityResolver
from narraint.queryengine.result import QueryResult, QueryResultBase


class QueryResultAggregationStrategy:

    def rank_results(self, results: [QueryResultBase]):
        raise NotImplementedError
