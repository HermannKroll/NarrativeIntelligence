from collections import defaultdict
from typing import List

from narraint.queryengine.aggregation.base import QueryResultAggregationStrategy
from narraint.queryengine.result import QueryDocumentResult, QueryDocumentResultList, QueryResultAggregate, \
    QueryResultAggregateList


class ResultTreeAggregationBySubstitution(QueryResultAggregationStrategy):
    """
    Ranks a list of query results by putting all documents sharing the same variable substitution into a group
    """

    def __init__(self):
        self.var_names = []
        self.aggregation = {}
        self.__doc_ids_per_aggregation = defaultdict(set)
        self.results = []
        self.doc_ids = set()
        self.root = QueryResultAggregateList()
        self.generated_tree_aggregates = {}
        self.varsubs2documents = defaultdict(list)

    def _clear_state(self):
        self.var_names.clear()
        self.aggregation.clear()
        self.__doc_ids_per_aggregation.clear()
        self.results.clear()
        self.doc_ids.clear()
        self.root = QueryResultAggregateList()
        self.generated_tree_aggregates.clear()
        self.varsubs2documents.clear()

    def rank_results(self, results: List[QueryDocumentResult], ordered_var_names: List[str] = None, freq_sort_desc=True,
                     year_sort_desc=True, start_pos=None, end_pos=None) -> [QueryDocumentResultList, bool]:
        self._clear_state()
        self.var_names = ordered_var_names

        results.sort(key=lambda x: (x.publication_year, x.publication_month), reverse=year_sort_desc)
        # variable is used
        if self.var_names:
            self.var_names = ordered_var_names
            for r in results:
                self._add_query_result(r)

            self._populate_tree_structure(freq_sort_desc)

           # self.root.sort_results_by_substitutions(freq_sort_desc)
            if start_pos and end_pos:
                self.root.set_slice(start_pos, end_pos)

            return self.root, True
        else:
            # no variable is used
            query_result = QueryDocumentResultList()
            for res in results:
                query_result.add_query_result(res)
            return query_result, False

    def _add_query_result_in_tree(self, results: List[QueryDocumentResult], parent: QueryResultAggregateList, level: int):
        # find the current substitution for this level
        level_var = self.var_names[level]
        substitution = results[0].var2substitution[level_var]
        key = (level_var, substitution.entity_id, substitution.entity_type)
        # check whether an aggregated query result node has been generated or generate it otherwise
        if key not in self.generated_tree_aggregates:
            var2sub = {level_var: substitution}
            node = QueryResultAggregate(var2sub)
            parent.add_query_result(node)
            self.generated_tree_aggregates[key] = node
        else:
            node = self.generated_tree_aggregates[key]
        # we are at the tree leaves - attach document result to node
        if level == len(self.var_names) - 1:
            # trick: documents are automatically added to leaves because they must have all subs for all vars
            for res in results:
                node.add_query_result(res)
        # we have to generate the next level
        else:
            # do we need to generate a new aggregate list?
            next_aggregated_list = QueryResultAggregateList()
            node.add_query_result(next_aggregated_list)
            self._add_query_result_in_tree(results, next_aggregated_list, level + 1)

    def _populate_tree_structure(self, freq_sort_desc):
        all_result_lists = []

        for _, results in self.varsubs2documents.items():
            all_result_lists.append((results, len(results)))
        all_result_lists.sort(key=lambda x: x[1], reverse=freq_sort_desc)

        for results, _ in all_result_lists:
            self._add_query_result_in_tree(results, self.root, 0)

    def _add_query_result(self, result: QueryDocumentResult):
        var_subs = set()
        for var_name in self.var_names:
            sub = result.var2substitution[var_name]
            var_subs.add((var_name, sub.entity_id, sub.entity_type))
        key = frozenset(var_subs)
        self.varsubs2documents[key].append(result)
