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
        self.level1_var_sub_count = defaultdict(int)
        self.level1_key_contained_in = defaultdict(set)

    def _clear_state(self):
        self.var_names.clear()
        self.aggregation.clear()
        self.__doc_ids_per_aggregation.clear()
        self.results.clear()
        self.doc_ids.clear()
        self.root = QueryResultAggregateList()
        self.generated_tree_aggregates.clear()
        self.varsubs2documents.clear()
        self.level1_var_sub_count.clear()
        self.level1_key_contained_in.clear()

    def rank_results(self, results: List[QueryDocumentResult], ordered_var_names: List[str] = None, freq_sort_desc=True,
                     year_sort_desc=True, start_pos=None, end_pos=None) -> [QueryDocumentResultList, bool]:
        self._clear_state()
        # retrieve the var names if not given
        if results and not ordered_var_names:
            self.var_names = sorted(list(results[0].var2substitution.keys()))
        else:
            self.var_names = ordered_var_names

        results.sort(key=lambda x: (x.publication_year, x.publication_month), reverse=year_sort_desc)
        # variable is used
        if self.var_names:
            for r in results:
                self._add_query_result_in_aggregation(r)

            self._populate_tree_structure(freq_sort_desc, start_pos, end_pos)

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

    def _generate_tree_structure(self):

        query_aggregate_lists = {1: self.root}

        # Go through all aggregated keys
        for var_sub_key in self.varsubs2documents.keys():
            # build all levels for the tree structure
            for level in range(1, len(self.var_names) + 1):
                # construct the current possible substitution on that level
                # e.g. X = A
                current_parent_key = var_sub_key[0:(level * 2 - 2)]
                current_sub = var_sub_key[0:level * 2]

                if not current_parent_key:
                    parent = self.root
                elif current_parent_key in query_aggregate_lists:
                    parent = query_aggregate_lists[current_parent_key]
                else:
                    parent = QueryResultAggregateList()
                    # we must put it under the corresponding aggregate node
                    parent_of_parent = self.generated_tree_aggregates[current_parent_key]
                    parent_of_parent.add_query_result(parent)
                    query_aggregate_lists[current_parent_key] = parent

                # Either we have already generated a tree node on that level
                # or we must do it now
                if current_sub not in self.generated_tree_aggregates:
                    var2sub = {}
                    for j in range((level-1)*2, len(current_sub), 2):
                        var2sub[current_sub[j]] = current_sub[j + 1]
                    node = QueryResultAggregate(var2sub)
                    parent.add_query_result(node)
                    self.generated_tree_aggregates[current_sub] = node

    def _populate_tree_structure(self, freq_sort_desc, start_pos, end_pos):
        all_result_lists = []

        # consider only substitutions that are on level 1 between start pos and end pos
        for key, results in self.varsubs2documents.items():
            all_result_lists.append((results, len(results)))
        all_result_lists.sort(key=lambda x: x[1], reverse=freq_sort_desc)

        # generate tree structure for all results
        self._generate_tree_structure()

        # populate the structure
        for key, results in self.varsubs2documents.items():
            self.generated_tree_aggregates[key].results = results

        # sort also all subtrees
        todo = [self.root]
        while todo:
            current_tree_node = todo.pop()
            current_tree_node.results.sort(key=lambda x: x.get_result_size(), reverse=freq_sort_desc)
            for res in current_tree_node.results:
                if isinstance(res, QueryResultAggregateList) or isinstance(res, QueryResultAggregate):
                    todo.append(res)

    def _add_query_result_in_aggregation(self, result: QueryDocumentResult):
        var_subs = list()
        for var_name in self.var_names:
            sub = result.var2substitution[var_name]
            var_subs.append(var_name)
            var_subs.append(sub)
        key = tuple(var_subs)
        self.varsubs2documents[key].append(result)
