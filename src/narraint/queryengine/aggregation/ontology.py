from collections import defaultdict

from narraint.queryengine.aggregation.base import QueryResultAggregationStrategy
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.result import QueryDocumentResult, QueryDocumentResultList, QueryResultAggregate, \
    QueryResultAggregateList, QueryEntitySubstitution
from narrant.entity.meshontology import MeSHOntology
from narrant.preprocessing.enttypes import DISEASE, CHEMICAL, DOSAGE_FORM, METHOD, LAB_METHOD

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
        self._pref_trees_visited = set()
        self._pref_tree_nodes_with_docs = set()

    def _clear_state(self):
        self.var_names.clear()
        self.aggregation.clear()
        self.__doc_ids_per_aggregation.clear()
        self.results.clear()
        self.doc_ids.clear()
        self.pref2result.clear()
        self._pref_trees_visited.clear()
        self._pref_tree_nodes_with_docs.clear()

    def rank_results(self, results: [QueryDocumentResult], freq_sort_desc, year_sort_desc):
        self._clear_state()
        self.freq_sort_desc = freq_sort_desc
        self.year_sort_desc = year_sort_desc

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
                        if substitution.entity_type in [CHEMICAL, DISEASE, DOSAGE_FORM, METHOD, LAB_METHOD]:
                            id_without_mesh = substitution.entity_id[5:]
                            try:
                                pref_tree_numbers = self.mesh_ontology.get_tree_numbers_for_descriptor(id_without_mesh)
                                for pref_t in pref_tree_numbers:
                                    prefix_substitution_list.append((pref_t, res.var2substitution[v]))
                                    prefix_document_result_list.append((pref_t, res))
                                    # this tree will have a document node
                                    self._pref_tree_nodes_with_docs.add(pref_t)
                            except KeyError:
                                misc_document_results[substitution.entity_type].append(res)
                        else:
                            misc_document_results[substitution.entity_type].append(res)
                    prefix_substitution_list.sort(key=lambda x: x[0])
                    var2prefix_substitution_list[v] = prefix_substitution_list
                    var2prefix_document_result_list[v] = prefix_document_result_list

                ent_type_aggregation = []
                if DOSAGE_FORM in retrieved_ent_types:
                    dosage_form_tree_0 = self._build_tree_structure(var2prefix_substitution_list, "FIDX")
                    dosage_form_tree_1 = self._build_tree_structure(var2prefix_substitution_list, "D26.255")
                    dosage_form_tree_2 = self._build_tree_structure(var2prefix_substitution_list, "E02.319.300")
                    dosage_form_tree_3 = self._build_tree_structure(var2prefix_substitution_list, "J01.637.512")
                    dosage_form_aggregation = self._create_query_aggregate("", "", DOSAGE_FORM, DOSAGE_FORM)
                    dosage_form_aggregation.add_query_result(dosage_form_tree_0)
                    dosage_form_aggregation.add_query_result(dosage_form_tree_1)
                    dosage_form_aggregation.add_query_result(dosage_form_tree_2)
                    dosage_form_aggregation.add_query_result(dosage_form_tree_3)
                    ent_type_aggregation.append((DOSAGE_FORM, dosage_form_aggregation))
                if METHOD in retrieved_ent_types or LAB_METHOD in retrieved_ent_types:
                    method_tree = self._build_tree_structure(var2prefix_substitution_list, "E")
                    method_aggregation = self._create_query_aggregate("", "", METHOD, METHOD)
                    method_aggregation.add_query_result(method_tree)
                    ent_type_aggregation.append((METHOD, method_aggregation))
                if CHEMICAL in retrieved_ent_types:
                    chemical_tree = self._build_tree_structure(var2prefix_substitution_list, "D")
                    chemical_aggregation = self._create_query_aggregate("", "", CHEMICAL, CHEMICAL)
                    chemical_aggregation.add_query_result(chemical_tree)
                    ent_type_aggregation.append((CHEMICAL, chemical_aggregation))
                if DISEASE in retrieved_ent_types:
                    disease_tree = self._build_tree_structure(var2prefix_substitution_list, "C")
                    disease_aggregation = self._create_query_aggregate("", "", DISEASE, DISEASE)
                    disease_aggregation.add_query_result(disease_tree)
                    ent_type_aggregation.append((DISEASE, disease_aggregation))
                self._populate_tree_structure(var2prefix_document_result_list)
                if misc_document_results:
                    for ent_type, document_results in misc_document_results.items():
                        document_results = misc_document_results[ent_type]
                        misc_aggregation_list = self.substitution_based_strategy.rank_results(document_results,
                                                                                              freq_sort_desc)
                        misc_aggregation = self._create_query_aggregate("", "", f'{ent_type} (No MeSH Taxonomy)',
                                                                        f'{ent_type} (No MeSH Taxonomy)')
                        misc_aggregation.add_query_result(misc_aggregation_list)
                        ent_type_aggregation.append((ent_type, misc_aggregation))

                resulting_tree = QueryResultAggregateList()
                for _, aggregation in sorted(ent_type_aggregation, key=lambda x: x[1].get_result_size(),
                                             reverse=self.freq_sort_desc):
                    self._sort_node_result_list(aggregation)
                    resulting_tree.add_query_result(aggregation)
                return resulting_tree
            else:
                # no variable is used
                query_result = QueryDocumentResultList()
                for res in results:
                    query_result.add_query_result(res)
                    query_result.results.sort(key=lambda x: (x.publication_year_int, int(x.month)),
                                              reverse=self.year_sort_desc)
                return query_result
        else:
            return QueryDocumentResultList()

    def _create_query_aggregate(self, ent_str, ent_id, ent_type, ent_name):
        var2sub = dict()
        var2sub[self.var_names[0]] = QueryEntitySubstitution(ent_str, ent_id, ent_type, ent_name)
        return QueryResultAggregate(var2sub)

    def _node_has_result_list(self, node):
        if isinstance(node, QueryResultAggregateList) or isinstance(node, QueryResultAggregate):
            return True
        return False

    def _sort_node_result_list(self, node):
        if self._node_has_result_list(node):
            result_docs = []
            for res in node.results:
                if self._node_has_result_list(res):
                    self._sort_node_result_list(res)
                if isinstance(res, QueryDocumentResult):
                    result_docs.append(res)
            node.results.sort(key=lambda x: x.get_result_size(), reverse=self.freq_sort_desc)
            if result_docs:
                for res in result_docs:
                    node.results.remove(res)
                result_docs.sort(key=lambda x: (x.publication_year_int, int(x.month)), reverse=self.year_sort_desc)
                node.results.extend(result_docs)

    def _populate_tree_structure(self, var2prefix_document_result_list):
        for v in self.var_names:
            for tree_prefix, doc_result in var2prefix_document_result_list[v]:
                try:
                    self.pref2result[tree_prefix].add_query_result(doc_result)
                except KeyError:
                    # we do not want to other trees than C or D
                    pass
                    # print('Error: no tree node for prefix {}'.format(tree_prefix))

    def _build_tree_structure(self, var2prefix_substitution_list, prefix_start="",
                              depth=0) -> QueryResultAggregateList():
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
                    pref_current = '.'.join(pref_split[0:depth + 1])
                    # do not visit pref twice
                    if pref_current in self._pref_trees_visited:
                        continue
                    self._pref_trees_visited.add(pref_current)
                    # search the descriptor for this tree
                    try:
                        pref_desc_id, pref_desc_name = self.mesh_ontology.get_descriptor_for_tree_no(pref_current)
                        pref_desc_id = 'MESH:' + pref_desc_id
                        pref_desc_name = pref_current + '.' + pref_desc_name
                        pref_desc_type = MeSHOntology.get_name_for_tree(pref[0])

                        pref_desc_substitution = QueryEntitySubstitution(pref_desc_name, pref_desc_id, pref_desc_type,
                                                                         pref_desc_name)
                        var2substitution = dict()
                        var2substitution[v] = pref_desc_substitution
                        next_res = self._build_tree_structure(var2prefix_substitution_list, pref_current, depth + 1)
                        # if the node has no document child and there is only one sub node - merge them
                        if pref_current not in self._pref_tree_nodes_with_docs and len(next_res.results) == 1:
                            results.add_query_result(next_res)
                            self.pref2result[pref_current] = next_res
                        else:
                            sub_results = QueryResultAggregate(var2substitution)
                            sub_results.add_query_result(next_res)
                            results.add_query_result(sub_results)
                            self.pref2result[pref_current] = sub_results
                    except KeyError as k:
                        print('keyerror: {}'.format(k))
        return results
