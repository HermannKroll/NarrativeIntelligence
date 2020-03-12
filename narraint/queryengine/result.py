from collections import defaultdict

from narraint.queryengine.entityresolver import EntityResolver


class QueryFactExplanation:

    def __init__(self, sentence, predicate, predicate_canonicalized):
        self.sentence = sentence
        self.predicate = predicate
        self.predicate_canonicalized = predicate_canonicalized

    def __str__(self):
        return '{} ("{}" -> "{}")'.format(self.sentence, self.predicate, self.predicate_canonicalized)


class QueryResult:

    def __init__(self, doc_id, title, var2substitution, confidence, explanations: [QueryFactExplanation]):
        self.doc_id = doc_id
        self.title = title
        self.var2substitution = var2substitution
        self.confidence = confidence
        self.explanations = explanations


class QueryResultAggregate:

    def __init__(self, var_names):
        self.result_size = 0
        self.var_names = var_names
        self.aggregation = {}
        self.__doc_ids_per_aggregation = defaultdict(set)
        self.results = []
        self.doc_ids = []
        self.entity_resolver = EntityResolver.instance()

    def add_query_result(self, result: QueryResult):
        self.result_size += 1
        self.results.append(result)
        self.doc_ids.append(result.doc_id)
        # build a key consisting of a list of variable substitutions
        values = []
        if self.var_names:
            for name in self.var_names:
                values.append(result.var2substitution[name].entity_id)
            key = frozenset(tuple(values))
        else:
            key = "DEFAULT"
        # add this document to the value based aggregation
        if key in self.aggregation:
            # skip already included documents
            if result.doc_id not in self.__doc_ids_per_aggregation[key]:
                self.aggregation[key][0].append(result)
                self.__doc_ids_per_aggregation[key].add(result.doc_id)
        else:
            self.__doc_ids_per_aggregation[key].add(result.doc_id)
            self.aggregation[key] = ([result], result.var2substitution)

    def __entity_to_str(self, entity):
        ent_name = self.entity_resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type)
        # if no name was found - return tagged name
        if ent_name == entity.entity_id:
            ent_name = entity.entity_str
        return '{} ({} {})'.format(ent_name, entity.entity_id, entity.entity_type)

    def get_doc_ids_per_substitution(self):
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
                var_substitution_strings.append(self.__entity_to_str(var2subs[v]))

            yield self.var_names, var_substitution_strings, doc_ids, doc_titles, explanations

    def get_and_rank_results(self):
        ranked_results = []
        for _, var_subs, doc_ids, doc_titles, explanations in self.get_doc_ids_per_substitution():
            ranked_results.append((len(doc_ids), var_subs, doc_ids, doc_titles, explanations))

        ranked_results.sort(key=lambda x: x[0], reverse=True)
        converted_results = []
        for _, var_subs, doc_ids, doc_titles, explanations in ranked_results:
            converted_results.append((self.var_names, var_subs, doc_ids, doc_titles, explanations))
        return converted_results
