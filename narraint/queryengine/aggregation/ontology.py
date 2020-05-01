from collections import defaultdict

from narraint.entity.enttypes import DISEASE, CHEMICAL
from narraint.entity.meshontology import MeSHOntology
from narraint.queryengine.aggregation.base import QueryResultAggregationStrategy
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.result import QueryDocumentResult, QueryDocumentResultList, QueryResultAggregate, \
    QueryResultAggregateList, QueryEntitySubstitution

MISCELLANEOUS_PREFIX = "Miscellaneous"


class ResultAggregationByOntology(QueryResultAggregationStrategy):
    """
    Ranks the results into a MeSH Ontology
    """

    def __init__(self):
        self.substitution_based_strategy = ResultAggregationBySubstitution()
        self.var_names = []
        self.aggregation = {}
        self.__doc_ids_per_aggregation = defaultdict(set)
        self.results = []
        self.doc_ids = []
        self.mesh_ontology = MeSHOntology.instance()
        self.pref2result = {}

    def _clear_state(self):
        self.var_names.clear()
        self.aggregation.clear()
        self.__doc_ids_per_aggregation.clear()
        self.results.clear()
        self.doc_ids.clear()
        self.pref2result.clear()

    def rank_results(self, results: [QueryDocumentResult]):
        self._clear_state()

        if results:
            self.var_names = sorted(list(results[0].var2substitution.keys()))
            if self.var_names:
                misc_document_results = defaultdict(list)
                var2prefix_substitution_list = {}
                var2prefix_document_result_list = {}
                retrieved_ent_types = set()
                for v in self.var_names:
                    prefix_substitution_list = []
                    prefix_document_result_list = []
                    for res in results:
                        substitution = res.var2substitution[v]
                        retrieved_ent_types.add(substitution.entity_type)
                        if substitution.entity_type in [CHEMICAL, DISEASE]:
                            id_without_mesh = substitution.entity_id[5:]
                            pref_tree_numbers = self.mesh_ontology.get_tree_numbers_for_descriptor(id_without_mesh)
                            for pref_t in pref_tree_numbers:
                                prefix_substitution_list.append((pref_t, res.var2substitution[v]))
                                prefix_document_result_list.append((pref_t, res))
                        else:
                            misc_document_results[substitution.entity_type].append(res)
                    prefix_substitution_list.sort(key=lambda x: x[0])
                    var2prefix_substitution_list[v] = prefix_substitution_list
                    var2prefix_document_result_list[v] = prefix_document_result_list

                resulting_tree = QueryResultAggregateList()
                ent_type_aggregation = []
                if CHEMICAL in retrieved_ent_types:
                    chemical_tree = self._build_tree_structure(var2prefix_substitution_list, "D")
                    chemical_aggregation = self._create_query_aggregate("", "", "", CHEMICAL)
                    chemical_aggregation.add_query_result(chemical_tree)
                    ent_type_aggregation.append((CHEMICAL, chemical_aggregation))
                if DISEASE in retrieved_ent_types:
                    disease_tree = self._build_tree_structure(var2prefix_substitution_list, "C")
                    disease_aggregation = self._create_query_aggregate("", "", "", DISEASE)
                    disease_aggregation.add_query_result(disease_tree)
                    ent_type_aggregation.append((DISEASE, disease_aggregation))
                self._populate_tree_structure(var2prefix_document_result_list)
                if misc_document_results:
                    for ent_type, document_results in misc_document_results.items():
                        document_results = misc_document_results[ent_type]
                        misc_aggregation_list = self.substitution_based_strategy.rank_results(document_results)
                        misc_aggregation = self._create_query_aggregate("", "", "", ent_type)
                        misc_aggregation.add_query_result(misc_aggregation_list)
                        ent_type_aggregation.append((ent_type, misc_aggregation))

                for _, aggregation in sorted(ent_type_aggregation, key=lambda x: x[0]):
                    resulting_tree.add_query_result(aggregation)
                return resulting_tree
            else:
                # no variable is used
                query_result = QueryDocumentResultList()
                for res in results:
                    query_result.add_query_result(res)
                return query_result
        else:
            return QueryDocumentResultList()

    def _create_query_aggregate(self, ent_str, ent_id, ent_type, ent_name):
        var2sub = dict()
        var2sub[self.var_names[0]] = QueryEntitySubstitution(ent_str, ent_id, ent_type, ent_name)
        return QueryResultAggregate(var2sub)

    def _populate_tree_structure(self, var2prefix_document_result_list):
        for v in self.var_names:
            for tree_prefix, doc_result in var2prefix_document_result_list[v]:
                try:
                    self.pref2result[tree_prefix].add_query_result(doc_result)
                except KeyError:
                    print('Error: no tree node for prefix {}'.format(tree_prefix))

    def _build_tree_structure(self, var2prefix_substitution_list, prefix_start="", depth=0):
        results = QueryResultAggregateList()
        for v in self.var_names:
            for pref, substitution in var2prefix_substitution_list[v]:
                if not pref.startswith(prefix_start):
                    continue
                # Check if the tree no was already processed
                if pref in self.pref2result:
                    continue
                # check if the prefix start is smaller than the full pref
                if len(prefix_start) < len(pref):
                    pref_split = pref.split('.')
                    # split the prefix tree at the current depth (e.g. depth 0 means first element)
                    pref_current = '.'.join(pref_split[0:depth+1])
                    # search the descriptor for this tree
                    try:
                        pref_desc_id, pref_desc_name = self.mesh_ontology.get_descriptor_for_tree_no(pref_current)
                        pref_desc_id = 'MESH:' + pref_desc_id
                        pref_desc_name = pref_current + '.' + pref_desc_name
                        if pref.startswith('C'):
                            pref_desc_type = DISEASE
                        elif pref.startswith('D'):
                            pref_desc_type = CHEMICAL
                        else:
                            pref_desc_type = "UNKNOWN"

                        pref_desc_substitution = QueryEntitySubstitution(pref_desc_name, pref_desc_id, pref_desc_type,
                                                                         pref_desc_name)
                        var2substitution = dict()
                        var2substitution[v] = pref_desc_substitution
                        next_res = self._build_tree_structure(var2prefix_substitution_list, pref_current, depth + 1)
                        # if there is only one sub node - merge them
                        if len(next_res.results) == 1:
                            results.add_query_result(next_res)
                        else:
                            sub_results = QueryResultAggregate(var2substitution)
                            sub_results.add_query_result(next_res)
                            results.add_query_result(sub_results)
                            self.pref2result[pref_current] = sub_results
                    except KeyError as k:
                        print('keyerror: {}'.format(k))
        return results
