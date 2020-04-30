from collections import defaultdict

from narraint.entity.entityresolver import EntityResolver
from narraint.queryengine.aggregation.base import QueryResultAggregationStrategy
from narraint.queryengine.result import QueryResult, QueryResultBase, QueryResultList, QueryResultAggregate, \
    QueryResultAggregateList


class ResultAggregationBySubstitution(QueryResultAggregationStrategy):

    def __init__(self):
        self.var_names = []
        self.aggregation = {}
        self.__doc_ids_per_aggregation = defaultdict(set)
        self.results = []
        self.doc_ids = []
        self.entity_resolver = EntityResolver.instance()

    def _clear_state(self):
        self.var_names.clear()
        self.aggregation.clear()
        self.__doc_ids_per_aggregation.clear()
        self.results.clear()
        self.doc_ids.clear()

    def rank_results(self, results: [QueryResultBase]):
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
                unsorted_list.append((len(query_aggregate.results), query_aggregate))

            # sort by amount of documents and create desired output
            query_result = QueryResultAggregateList()
            unsorted_list.sort(key=lambda x: x[0], reverse=True)
            for _, res in unsorted_list:
                query_result.add_query_result(res)
            return query_result
        else:
            # no variable is used
            query_result = QueryResultList()
            for _, (results, var2subs) in self.aggregation.items():
                for res in results:
                    query_result.add_query_result(res)
            return query_result
      #  ranked_results = []
      #  for _, var_subs, doc_ids, doc_titles, explanations in self._get_doc_ids_per_substitution():
      #      ranked_results.append((len(doc_ids), var_subs, doc_ids, doc_titles, explanations))

      #  ranked_results.sort(key=lambda x: x[0], reverse=True)
      #  converted_results = []
      #  for _, var_subs, doc_ids, doc_titles, explanations in ranked_results:
      #      converted_results.append((self.var_names, var_subs, doc_ids, doc_titles, explanations))
      #  return converted_results

    def _add_query_result(self, result: QueryResult):
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

    def _entity_to_str(self, entity):
        if entity.entity_type == 'predicate':
            return entity.entity_id  # id is already the name
        try:
            ent_name = self.entity_resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type)
        except KeyError:
            ent_name = entity.entity_str
        return '{} ({} {})'.format(ent_name, entity.entity_id, entity.entity_type)

    def _get_doc_ids_per_substitution(self):
        for _, (results, var2subs) in self.aggregation.items():
            doc_ids = []
            doc_titles = []
            explanations = []
            for r in results:
                doc_ids.append(r.doc_id)
                doc_titles.append(r.title)

                explanations_for_doc = []
                for e in r.explanations:
                    explanations_for_doc.append(str(e))
                explanations.append(explanations_for_doc)

            var_substitution_strings = []
            for v in self.var_names:
                var_substitution_strings.append(self._entity_to_str(var2subs[v]))

            yield self.var_names, var_substitution_strings, doc_ids, doc_titles, explanations
