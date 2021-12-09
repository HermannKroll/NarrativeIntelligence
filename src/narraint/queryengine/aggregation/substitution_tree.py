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
        self.var_names = ordered_var_names

        results.sort(key=lambda x: (x.publication_year, x.publication_month), reverse=year_sort_desc)
        # variable is used
        if self.var_names:
            self.var_names = ordered_var_names
            for r in results:
                self._add_query_result(r)

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

    def _populate_tree_structure(self, freq_sort_desc, start_pos, end_pos):
        all_result_lists = []

        # compute the most frequent substitutions for level 1 var
      #  level1_var_count = [(key, count) for key, count in self.level1_var_sub_count.items()]
      #  level1_var_count.sort(key=lambda x: x[1], reverse=freq_sort_desc)
     #   if start_pos < len(level1_var_count):
      #      if end_pos <= len(level1_var_count):
       #         level1_frequent_keys = {key for key, _ in level1_var_count[start_pos:end_pos]}
        #    else:
         #       level1_frequent_keys = {key for key, _ in level1_var_count[start_pos:end_pos]}
        #else:
         #   level1_frequent_keys = {key for key, _ in level1_var_count}

        # only keep the relevant level 1 keys here
        #self.level1_key_contained_in = {key for k, subkey in self.level1_key_contained_in.items()
         #                               if k in level1_frequent_keys
          #                              for key in subkey}

        # consider only substitutions that are on level 1 between start pos and end pos
        for key, results in self.varsubs2documents.items():
      #      if key in self.level1_key_contained_in:
            all_result_lists.append((results, len(results)))
        all_result_lists.sort(key=lambda x: x[1], reverse=freq_sort_desc)

        for results, _ in all_result_lists:
            self._add_query_result_in_tree(results, self.root, 0)

        #self.root.results.sort(key=lambda x: x.get_result_size(), reverse=freq_sort_desc)
        #for var_name in self.var_names[1:]:
        # sort also all subtrees
        todo = [self.root]
        while todo:
            current_tree_node = todo.pop()
            current_tree_node.results.sort(key=lambda x: x.get_result_size(), reverse=freq_sort_desc)
            for res in current_tree_node.results:
                if isinstance(res, QueryResultAggregateList) or isinstance(res, QueryResultAggregate):
                    todo.append(res)


    def _add_query_result(self, result: QueryDocumentResult):
      #  level1_var_sub = result.var2substitution[self.var_names[0]]
      #  leve1_var_sub_key = (self.var_names[0], level1_var_sub.entity_id, level1_var_sub.entity_type)
      #  self.level1_var_sub_count[leve1_var_sub_key] += 1

        var_subs = set()
        for var_name in self.var_names:
            sub = result.var2substitution[var_name]
            var_subs.add((var_name, sub.entity_id, sub.entity_type))
        key = frozenset(var_subs)

     #   self.level1_key_contained_in[leve1_var_sub_key].add(key)
        self.varsubs2documents[key].append(result)
