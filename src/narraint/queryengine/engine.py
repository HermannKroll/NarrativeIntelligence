import itertools
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Set, Dict, List

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, Sentence, PredicationDenorm, DocumentMetadataService
from narraint.queryengine.expander import QueryExpander
from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import DO_NOT_CARE_PREDICATE, ENTITY_TYPE_EXPANSION, VAR_NAME, VAR_TYPE
from narraint.queryengine.result import QueryFactExplanation, QueryEntitySubstitution, QueryExplanation, \
    QueryDocumentResult


class QueryEngine:

    @staticmethod
    def query_provenance_information(provenance: Dict[int, Set[int]]) -> QueryExplanation:
        """
        Queries Provenance information from the database
        :param provenance: a dict that maps a fact pattern index to a set of explaining predication ids
        :return: an QueryExplanation object
        """
        predication_ids = set()
        for _, pred_ids in provenance.items():
            predication_ids.update(pred_ids)

        session = SessionExtended.get()
        query = session.query(Predication.id,
                              Predication.sentence_id, Predication.predicate, Predication.relation,
                              Predication.subject_str, Predication.object_str, Predication.confidence) \
            .filter(Predication.id.in_(predication_ids))

        prov_id2fp_idx = defaultdict(set)
        for fact_idx, prov_ids in provenance.items():
            for p_id in prov_ids:
                prov_id2fp_idx[p_id].add(fact_idx)

        sentence_ids = set()
        query_explanation = QueryExplanation()
        for r in query:
            sentence_ids.add(r[1])
            for fp_idx in prov_id2fp_idx[r[0]]:
                query_explanation.integrate_explanation(
                    QueryFactExplanation(fp_idx, r[1], r[2], r[3], r[4], r[5], r[6], r[0]))

        # replace all sentence ids by sentence str
        id2sentence = QueryEngine.query_sentences_for_sent_ids(sentence_ids)
        for e in query_explanation.explanations:
            e.sentence = id2sentence[e.sentence]

        return query_explanation

    @staticmethod
    def query_metadata_for_doc_ids(doc_ids: Set[int], document_collection: str):
        """
        Query the title, author, journals etc. for a set of doc ids and a document collection
        :param doc_ids: a set of doc ids
        :param document_collection: the corresponding document collection
        :return: dict mapping docids to titles, dict mapping sentence ids to sentence texts
        """
        session = SessionExtended.get()
        # Query the document titles
        q_titles = session.query(DocumentMetadataService) \
            .filter(DocumentMetadataService.document_collection == document_collection) \
            .filter(DocumentMetadataService.document_id.in_(doc_ids))
        doc2metadata = {}
        for r in q_titles:
            title, authors, journals, year = r.title, r.authors, r.journals, r.publication_year
            if len(title) > 500:
                logging.debug('Large title detected: {}'.format(r.title))
                title = title[0:500]
            doc2metadata[int(r.document_id)] = (title, authors, journals, year)

        return doc2metadata

    @staticmethod
    def query_sentences_for_sent_ids(sentence_ids: Set[int]):
        """
        Query the sentences for a set of doc ids and sentence ids
        :param sentence_ids: a set of sentence ids
        :return: dict mapping docids to titles, dict mapping sentence ids to sentence texts
        """
        session = SessionExtended.get()
        # Query the sentences
        q_sentences = session.query(Sentence.id, Sentence.text).filter(Sentence.id.in_(sentence_ids))
        id2sentences = {}
        for r in q_sentences:
            sent = r[1]
            if len(sent) > 1500:
                logging.debug('long sentence detected for: {}'.format(r[0]))
                sent = '{}[...]'.format(sent[0:1500])
            id2sentences[int(r[0])] = sent

        return id2sentences

    @staticmethod
    def query_inverted_index_for_fact_pattern(fact_pattern: FactPattern, document_collection_filter: Set[str] = None):
        """
        Queries the Predication_Denorm Table for a specific fact pattern
        :param fact_pattern: a fact pattern
        :param document_collection_filter: only keep extraction from these document collections
        :return: provenance mapping, var2subs
        """
        session = SessionExtended.get()
        query = session.query(PredicationDenorm)
        # directly check predicate
        if fact_pattern.predicate != DO_NOT_CARE_PREDICATE:
            query = query.filter(PredicationDenorm.relation == fact_pattern.predicate)

        var_names_in_query = []
        subject_types, object_types = [], []
        # check subjects
        if len(fact_pattern.subjects) > 1:
            query = query.filter(PredicationDenorm.subject_id.in_([s.entity_id for s in fact_pattern.subjects]))
            subject_types = [s.entity_type for s in fact_pattern.subjects]
        elif len(fact_pattern.subjects) == 1:
            s = next(iter(fact_pattern.subjects))
            if s.entity_id.startswith('?'):
                # check variable
                var_name = VAR_NAME.search(s.entity_id)
                if not var_name:
                    raise ValueError('Variable name does not match regex: {}'.format(s.entity_id))
                var_name = var_name.group(1)
                var_names_in_query.append((var_name, 'subject'))
                var_type = VAR_TYPE.search(s.entity_id)
                if var_type:
                    var_type = var_type.group(1)
                    subject_types = [var_type]
            else:
                query = query.filter(PredicationDenorm.subject_id == s.entity_id)
                subject_types = [s.entity_type]

        # check objects
        if len(fact_pattern.objects) > 1:
            query = query.filter(PredicationDenorm.object_id.in_([o.entity_id for o in fact_pattern.objects]))
            object_types = [o.entity_type for o in fact_pattern.objects]
        elif len(fact_pattern.objects) == 1:
            o = next(iter(fact_pattern.objects))
            if o.entity_id.startswith('?'):
                # check variable
                var_name = VAR_NAME.search(o.entity_id)
                if not var_name:
                    raise ValueError('Variable name does not match regex: {}'.format(o.entity_id))
                var_name = var_name.group(1)
                var_names_in_query.append((var_name, 'object'))
                var_type = VAR_TYPE.search(o.entity_id)
                if var_type:
                    var_type = var_type.group(1)
                    object_types = [var_type]
                    if var_type in ENTITY_TYPE_EXPANSION:
                        query = query.filter(PredicationDenorm.object_type.in_(ENTITY_TYPE_EXPANSION[var_type]))
                    else:
                        query = query.filter(PredicationDenorm.object_type == var_type)
            else:
                query = query.filter(PredicationDenorm.object_id == o.entity_id)
                object_types = [o.entity_type]

        # check the subject types
        subject_types = QueryExpander.expand_entity_types(subject_types)
        if len(subject_types) > 1:
            query = query.filter(PredicationDenorm.subject_type.in_(subject_types))
        elif len(subject_types) == 1:
            query = query.filter(PredicationDenorm.subject_type == subject_types[0])
        else:
            pass

        # check the object types
        object_types = QueryExpander.expand_entity_types(object_types)
        if len(object_types) > 1:
            query = query.filter(PredicationDenorm.object_type.in_(object_types))
        elif len(object_types) == 1:
            query = query.filter(PredicationDenorm.object_type == object_types[0])
        else:
            pass

        # if the query asks for a class as subject or object
        # then use the class name as a variable name for the results
        subject_class = fact_pattern.get_subject_class()
        if subject_class:
            var_names_in_query.append((subject_class, "subject"))
        object_class = fact_pattern.get_object_class()
        if object_class:
            var_names_in_query.append((object_class, "object"))

        # execute the query
        provenance_mappings = []
        # compute the list of substitutions for the variables
        var2subs = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        var2subs_to_prove = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        for result in query:
            prov_mapping = json.loads(result.provenance_mapping)

            # Apply document collection filter
            if document_collection_filter and len(document_collection_filter) > 0:
                # keep only relevant document collection
                prov_mapping = {d_col: v for d_col, v in prov_mapping.items() if d_col in document_collection_filter}

            # Compute the hash dictionaries and indexes to the data
            provenance_mappings.append(prov_mapping)
            for doc_col, docids2prov in prov_mapping.items():
                doc_ids = docids2prov.keys()
                for var_name, position in var_names_in_query:
                    sub_id, sub_type = None, None
                    if position == 'subject':
                        sub_id, sub_type = result.subject_id, result.subject_type
                    elif position == 'object':
                        sub_id, sub_type = result.object_id, result.object_type
                    var2subs[var_name][doc_col][(sub_id, sub_type)].update({doc_id for doc_id in doc_ids})
                    for doc_id in doc_ids:
                        var2subs_to_prove[doc_col][doc_id][(var_name, sub_id, sub_type)].update(docids2prov[doc_id])
        return provenance_mappings, var2subs, var2subs_to_prove

    @staticmethod
    def merge_var2subs(var2subs, var2subs_updates):
        for var_name in var2subs_updates:
            for doc_col in var2subs_updates[var_name]:
                for sub_key in var2subs_updates[var_name][doc_col]:
                    doc_ids = var2subs_updates[var_name][doc_col][sub_key]
                    var2subs[var_name][doc_col][sub_key].update(doc_ids)

    @staticmethod
    def process_query_with_expansion(graph_query: GraphQuery, document_collection_filter: Set[str] = None) \
            -> List[QueryDocumentResult]:
        """
        Computes a GraphQuery
        The query will automatically be expanded and optimized
        :param graph_query: a graph query object
        :param document_collection_filter: only keep extraction from these document collections
        :return: a list of QueryDocumentResults
        """
        start_time = datetime.now()
        graph_query = QueryOptimizer.optimize_query(graph_query)
        if not graph_query:
            logging.debug('Query will not yield results - returning empty list')
            return []

        collection2valid_doc_ids = defaultdict(set)
        collection2valid_subs = {}
        fp2prov_mappings = {}
        fp2var_prov_mappings = {}
        logging.debug(f'Executing query {graph_query}...')
        for idx, fact_pattern in enumerate(graph_query):
            prov_mappings, var2subs, v2prov = QueryEngine.query_inverted_index_for_fact_pattern(fact_pattern,
                                                                                                document_collection_filter=document_collection_filter)
            # must the fact pattern be expanded?
            for e_fp in QueryExpander.expand_fact_pattern(fact_pattern):
                logging.debug(f'Expand {fact_pattern} to {e_fp}')
                pm_ex, var2subs_ex, v2prov_ex = QueryEngine.query_inverted_index_for_fact_pattern(e_fp,
                                                                                                  document_collection_filter=document_collection_filter)
                QueryEngine.merge_var2subs(var2subs, var2subs_ex)
                QueryEngine.merge_var2subs(v2prov, v2prov_ex)
                prov_mappings.extend(pm_ex)

            fp2var_prov_mappings[idx] = v2prov
            fp2prov_mappings[idx] = prov_mappings
            # check that facts are matched within the same documents
            doc_ids_for_fp = set()
            doc_col_for_fp = set()
            for pm in prov_mappings:
                for d_col, docids2provids in pm.items():
                    doc_col_for_fp.add(d_col)
                    doc_ids_for_fp.update(docids2provids.keys())
            for d_col in doc_col_for_fp:
                if idx == 0:
                    collection2valid_doc_ids[d_col].update(doc_ids_for_fp)
                else:
                    collection2valid_doc_ids[d_col] = collection2valid_doc_ids[d_col].intersection(doc_ids_for_fp)

            # fact pattern has a variable
            if len(var2subs) > 0:
                for var_name in var2subs:
                    # first time we saw this variable
                    if var_name not in collection2valid_subs:
                        collection2valid_subs[var_name] = var2subs[var_name]
                    # oh no, we saw that variable before - check compatible substitutions
                    else:
                        compatible_var_subs = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
                        for doc_col in collection2valid_subs[var_name]:
                            # go through all already known substitutions
                            # we retrieve a dict mapping substitutions to sets of document ids
                            known_sub_keys = set(collection2valid_subs[var_name][doc_col].keys())
                            new_sub_keys = set(var2subs[var_name][doc_col].keys())
                            # keep only substitutions that are shared by both fact patterns
                            valid_sub_keys = known_sub_keys.intersection(new_sub_keys)

                            for (sub_id, sub_type) in valid_sub_keys:
                                # retrieve known document ids that support the substitution
                                known_doc_ids = set(collection2valid_subs[var_name][doc_col][(sub_id, sub_type)])
                                new_doc_ids = set(var2subs[var_name][doc_col][(sub_id, sub_type)])
                                valid_doc_ids_for_sub = known_doc_ids.intersection(new_doc_ids)
                                # only store substitutions for the variable that has document support for both
                                # fact patterns
                                if len(valid_doc_ids_for_sub) > 1:
                                    compatible_var_subs[var_name][doc_col][(sub_id, sub_type)] = valid_doc_ids_for_sub
                        # compatibility was checked
                        collection2valid_subs[var_name] = compatible_var_subs[var_name]
                        # compute all possible document ids that have compatible substitutions
                        for d_col in collection2valid_subs[var_name]:
                            compatible_doc_ids = set()
                            for d_ids in collection2valid_subs[var_name][d_col].values():
                                compatible_doc_ids.update(d_ids)
                            # now restrict the valid document ids to compatible document ids
                            collection2valid_doc_ids[d_col] = collection2valid_doc_ids[d_col].intersection(
                                compatible_doc_ids)

        # compute
        fp2prov_mappings_valid = {}
        for idx, _ in enumerate(graph_query):
            pm_valids = defaultdict(lambda: defaultdict(set))
            for pm in fp2prov_mappings[idx]:
                for doc_col, valid_d_ids in collection2valid_doc_ids.items():
                    for d_id, prov_ids in pm[doc_col].items():
                        if d_id in valid_d_ids:
                            pm_valids[doc_col][d_id].update(prov_ids)
            fp2prov_mappings_valid[idx] = pm_valids

        logging.debug(f'Query computed in {datetime.now() - start_time}s')
        # Construct the results
        # query document titles
        query_results = []

        # No variables are used in the query
        if len(collection2valid_subs) == 0:
            for d_col, d_ids in collection2valid_doc_ids.items():
                doc2metadata = QueryEngine.query_metadata_for_doc_ids(d_ids, d_col)
                for d_id in d_ids:
                    title, authors, journals, year = doc2metadata[int(d_id)]
                    fp2prov = {}
                    for idx, _ in enumerate(graph_query):
                        fp2prov[idx] = fp2prov_mappings_valid[idx][d_col][d_id]
                    query_results.append(QueryDocumentResult(int(d_id), title, authors, journals, year,
                                                             {}, 0.0, fp2prov))
        else:
            for d_col, d_ids in collection2valid_doc_ids.items():
                doc2metadata = QueryEngine.query_metadata_for_doc_ids(d_ids, d_col)

                doc2substitution = defaultdict(lambda: defaultdict(set))
                for var_name in collection2valid_subs:
                    for sub, sub_doc_ids in collection2valid_subs[var_name][d_col].items():
                        for d_id in sub_doc_ids:
                            if d_id in d_ids:
                                doc2substitution[d_id][var_name].add((sub[0], sub[1]))

                var_names = list([v for v in collection2valid_subs])
                for d_id, var2sub in doc2substitution.items():
                    list_of_substitutions = []
                    for var_name in var_names:
                        list_of_substitutions.append(list(doc2substitution[d_id][var_name]))

                    # There might be a document d1 which has ?X = 1 and ?X = 2 as well as ?Y = a
                    # then we must sort the document into the following groups (?X1 = 1, ?Y= a) and (?X = 2, ?Y = a)
                    shared_substitutions = itertools.product(*list_of_substitutions)
                    # Easy situation: List of substitutions for a single variable
                    for shared_sub in shared_substitutions:
                        var2sub_for_doc = {}
                        for idx, var_name in enumerate(var_names):
                            var2sub_for_doc[var_name] = QueryEntitySubstitution("", shared_sub[idx][0],
                                                                                shared_sub[idx][1])

                        title, authors, journals, year = doc2metadata[int(d_id)]
                        fp2prov = defaultdict(set)
                        for idx, fp in enumerate(graph_query):
                            if fp.has_variable():
                                fp_vars = fp.get_variable_names()
                                for v_idx, v_name in enumerate(var_names):
                                    if v_name in fp_vars:
                                        sub_key = (v_name, shared_sub[v_idx][0], shared_sub[v_idx][1])
                                        fp2prov[idx].update(fp2var_prov_mappings[idx][d_col][d_id][sub_key])
                            else:
                                fp2prov[idx] = fp2prov_mappings_valid[idx][d_col][d_id]

                        query_results.append(QueryDocumentResult(int(d_id), title, authors, journals, year,
                                                                 var2sub_for_doc, 0.0, fp2prov))

        query_results.sort(key=lambda x: x.document_id, reverse=True)
        return query_results

    @staticmethod
    def query_predicates(collection=None):
        session = SessionExtended.get()
        if not collection:
            query = session.query(Predication.predicate.distinct()). \
                filter(Predication.predicate.isnot(None))
        else:
            query = session.query(Predication.predicate.distinct()). \
                filter(Predication.predicate.isnot(None)). \
                filter(Predication.document_collection == collection)
        predicates = []
        start_time = datetime.now()
        for r in session.execute(query):
            predicates.append(r[0])

        logging.info('{} predicates queried in {}s'.format(len(predicates), datetime.now() - start_time))
        return predicates

    @staticmethod
    def query_entities():
        session = SessionExtended.get()
        query_subjects = session.query(Predication.subject_id, Predication.subject_str,
                                       Predication.subject_type).distinct()
        query_subjects = query_subjects.filter(Predication.relation.isnot(None))
        query_objects = session.query(Predication.object_id, Predication.object_str, Predication.object_type).distinct()
        query_objects = query_objects.filter(Predication.relation.isnot(None))
        query = query_subjects.union(query_objects).distinct()

        entities = set()
        start_time = datetime.now()
        for r in session.execute(query):
            ent_id, ent_str, ent_type = r[0], r[1], r[2]
            entities.add((ent_id, ent_str, ent_type))

        logging.info('{} entities queried in {}s'.format(len(entities), datetime.now() - start_time))
        return entities
