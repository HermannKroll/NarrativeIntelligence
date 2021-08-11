from collections import defaultdict

from narraint.queryengine.aggregation.base import QueryResultAggregationStrategy
from narraint.queryengine.result import QueryDocumentResult, QueryDocumentResultList, QueryResultAggregate, \
    QueryResultAggregateList


class ResultAggregationBySubstitution(QueryResultAggregationStrategy):
    """
    Ranks a list of query results by putting all documents sharing the same variable substitution into a group
    """

    def __init__(self):
        self.var_names = []
        self.aggregation = {}
        self.__doc_ids_per_aggregation = defaultdict(set)
        self.results = []
        self.doc_ids = []

    def _clear_state(self):
        self.var_names.clear()
        self.aggregation.clear()
        self.__doc_ids_per_aggregation.clear()
        self.results.clear()
        self.doc_ids.clear()

    def rank_results(self, results: [QueryDocumentResult], freq_sort_desc, year_sort_desc, end_pos=None):
        self._clear_state()
        for r in results:
            self._add_query_result(r)

        # variable is used
        if self.var_names:
            unsorted_list = []
            for _, (results, var2subs) in self.aggregation.items():
                query_aggregate = QueryResultAggregate(var2subs)
                for res in results:
                    query_aggregate.add_query_result(res)
                query_aggregate.sort_results_by_date(year_sort_desc)
                unsorted_list.append((len(query_aggregate.results), query_aggregate))

            # sort by amount of documents and create desired output
            query_result = QueryResultAggregateList()
            unsorted_list.sort(key=lambda x: x[0], reverse=freq_sort_desc)
            for _, res in unsorted_list:
                query_result.add_query_result(res)
            query_result.set_slice(end_pos)
            return query_result
        else:
            # no variable is used
            query_result = QueryDocumentResultList()
            for _, (results, var2subs) in self.aggregation.items():
                for res in results:
                    query_result.add_query_result(res)
            return query_result

    def _add_query_result(self, result: QueryDocumentResult):
        if not self.var_names:
            self.var_names = sorted(list(result.var2substitution.keys()))
        self.results.append(result)
        self.doc_ids.append(result.document_id)
        # build a key consisting of a list of variable substitutions
        values = []
        if self.var_names:
            for name in self.var_names:
                sub = result.var2substitution[name]
                values.append('{}{}'.format(sub.entity_type, sub.entity_id))
            key = frozenset(tuple(values))
        else:
            key = "DEFAULT"
        # add this document to the value based aggregation
        if key in self.aggregation:
            # skip already included documents
            #if result.doc_id in self.__doc_ids_per_aggregation[key]:
            self.aggregation[key][0].append(result)
            self.__doc_ids_per_aggregation[key].add(result.document_id)
        else:
            self.__doc_ids_per_aggregation[key].add(result.document_id)
            self.aggregation[key] = ([result], result.var2substitution)