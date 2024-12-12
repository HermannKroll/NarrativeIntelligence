import ast
import itertools
import logging
from collections import defaultdict
from datetime import datetime
from typing import Set, Dict, List

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, Sentence, \
    PredicationInvertedIndex, DocumentMetadataService, TagInvertedIndex, TermInvertedIndex
from narraint.queryengine.expander import QueryExpander
from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import DO_NOT_CARE_PREDICATE, VAR_NAME, VAR_TYPE, ENTITY_TYPE_VARIABLE
from narraint.queryengine.result import QueryFactExplanation, QueryEntitySubstitution, QueryExplanation, \
    QueryDocumentResult
from narrant.entity.entity import Entity

QUERY_DOCUMENT_LIMIT = 1500000


class QueryEngine:

    @staticmethod
    def enrich_document_results_with_metadata(documents: [QueryDocumentResult], collection2ids: dict) -> [
        QueryDocumentResult]:
        """
        Enriches a set of document results with document metadata
        :param documents: a list of document results
        :param collection2ids: a dictionary mapping doc collections to id sets
        :return:
        """
        filtered_document_results = []
        for d_col, d_ids in collection2ids.items():
            doc2metadata = QueryEngine.query_metadata_for_doc_ids(d_ids, d_col)

            for d in documents:
                # check whether document belongs to that collection
                if d.document_collection == d_col:
                    # only add documents that have metadata
                    if d.document_id in doc2metadata:
                        title, authors, journals, year, month, doi, org_id, doc_classes = doc2metadata[d.document_id]
                        d.title = title
                        d.authors = authors
                        d.journals = journals
                        d.publication_year = year
                        d.publication_month = month
                        d.doi = doi
                        d.org_document_id = org_id
                        d.document_classes = doc_classes

                        filtered_document_results.append(d)

        return filtered_document_results

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
    def replace_variables_with_entities(graph_query: GraphQuery, var_mapping: str):
        logging.debug(f'Replacing variables with entities using "{var_mapping}"')
        variables2entities = dict()
        for mapping in var_mapping.split(";"):
            variable, entity_id, entity_type = mapping.split("|")
            variables2entities[variable + "(" + entity_type + ")"] = (entity_id, entity_type)

        for fp in graph_query.fact_patterns:
            if len(fp.subjects) == 1 and fp.subjects[0].entity_type == ENTITY_TYPE_VARIABLE:
                entity_id, entity_type = variables2entities[fp.subjects[0].entity_id]
                fp.subjects = [Entity(entity_id, entity_type)]

            if len(fp.objects) == 1 and fp.objects[0].entity_type == ENTITY_TYPE_VARIABLE:
                entity_id, entity_type = variables2entities[fp.objects[0].entity_id]
                fp.objects = [Entity(entity_id, entity_type)]

        return graph_query

    @staticmethod
    def explain_document(document_id: str, document_collection: str, graph_query: GraphQuery,
                         variables: str = "") -> QueryExplanation:
        """
        Queries Provenance information from the database for the given document with respect to the current query
        :param document_id: document id that requires provenance information
        :param document_collection: collection of the document
        :param graph_query: query representation
        :param variables: string of optional variable mappings
        :return: a QueryExplanation object
        """
        query_explanation = QueryExplanation()

        # we do not allow variables
        if any(fp.has_variable() for fp in graph_query):
            if not variables:
                logging.error("Provenance requires non-variable fact-patterns but no variable mappings were provided")
                return query_explanation

            graph_query = QueryEngine.replace_variables_with_entities(graph_query, variables)

        graph_query = QueryOptimizer.optimize_query(graph_query)
        if not graph_query:
            logging.error('Query will not yield results.')
            return query_explanation

        logging.debug("Query provenance information for doc {} ({})".format(document_id, document_collection))

        # retrieve all predications for the provided document
        session = SessionExtended.get()
        query = session.query(Predication.id, Predication.sentence_id, Predication.predicate, Predication.relation,
                              Predication.subject_str, Predication.subject_id, Predication.subject_type,
                              Predication.object_str, Predication.object_id, Predication.object_type,
                              Predication.confidence)
        query = query.filter(Predication.document_id == document_id)
        query = query.filter(Predication.document_collection == document_collection)

        if query.count() == 0:
            logging.error('No predications for the document exist')
            return query_explanation

        sentence_ids = set()

        # query for each fact pattern
        for index, fp in enumerate(graph_query.fact_patterns):
            subject_ids = set(s.entity_id for s in fp.subjects)
            subject_types = set(s.entity_type for s in fp.subjects)
            predicates = {fp.predicate}
            object_ids = set(o.entity_id for o in fp.objects)
            object_types = set(o.entity_type for o in fp.objects)

            for expanded_fp in QueryExpander.expand_fact_pattern(fp):
                subject_ids.update(s.entity_id for s in expanded_fp.subjects)
                subject_types.update((s.entity_type for s in expanded_fp.subjects))
                predicates.add(expanded_fp.predicate)
                object_ids.update(o.entity_id for o in expanded_fp.objects)
                object_types.update(o.entity_type for o in expanded_fp.objects)

            # ignore predicate when type equals "associated"
            ignore_predicate = (len(predicates) == 1 and list(predicates)[0] == DO_NOT_CARE_PREDICATE)

            # match fact patterns against predications
            for r in query:
                if (r.subject_id in subject_ids and r.subject_type in subject_types
                        and r.object_id in object_ids and r.object_type in object_types
                        and (ignore_predicate or r.relation in predicates)):
                    fact_explanation = QueryFactExplanation(str(index), r.sentence_id, r.predicate, r.relation,
                                                            r.subject_str, r.object_str, r.confidence, r.id)
                    query_explanation.integrate_explanation(fact_explanation)
                    sentence_ids.add(r.sentence_id)

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
            title, authors, journals, year, month, doi, org_id = r.title, r.authors, r.journals, r.publication_year, \
                r.publication_month, r.publication_doi, \
                r.document_id_original
            doc_classes = None
            if r.document_classifications:
                doc_classes = ast.literal_eval(r.document_classifications)

            if len(title) > 500:
                logging.debug('Large title detected: {}'.format(r.title))
                title = title[0:500]
            doc2metadata[int(r.document_id)] = (title, authors, journals, year, month, doi, org_id, doc_classes)

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
        query = session.query(PredicationInvertedIndex)

        # check document collections
        if len(document_collection_filter) == 1:
            # then just check the first element of the set
            query = query.filter(PredicationInvertedIndex.document_collection == next(iter(document_collection_filter)))
        if len(document_collection_filter) > 1:
            query = query.filter(PredicationInvertedIndex.document_collection.in_(document_collection_filter))

        # directly check predicate
        if fact_pattern.predicate != DO_NOT_CARE_PREDICATE:
            query = query.filter(PredicationInvertedIndex.relation == fact_pattern.predicate)

        var_names_in_query = []
        subject_types, object_types = [], []
        # check subjects
        if len(fact_pattern.subjects) > 1:
            query = query.filter(PredicationInvertedIndex.subject_id.in_([s.entity_id for s in fact_pattern.subjects]))
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
                query = query.filter(PredicationInvertedIndex.subject_id == s.entity_id)
                subject_types = [s.entity_type]

        # check objects
        if len(fact_pattern.objects) > 1:
            query = query.filter(PredicationInvertedIndex.object_id.in_([o.entity_id for o in fact_pattern.objects]))
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
            else:
                query = query.filter(PredicationInvertedIndex.object_id == o.entity_id)
                object_types = [o.entity_type]

        # check the subject types
        subject_types = QueryExpander.expand_entity_types(subject_types)
        if len(subject_types) > 1:
            query = query.filter(PredicationInvertedIndex.subject_type.in_(subject_types))
        elif len(subject_types) == 1:
            query = query.filter(PredicationInvertedIndex.subject_type == subject_types[0])

        # check the object types
        object_types = QueryExpander.expand_entity_types(object_types)
        if len(object_types) > 1:
            query = query.filter(PredicationInvertedIndex.object_type.in_(object_types))
        elif len(object_types) == 1:
            query = query.filter(PredicationInvertedIndex.object_type == object_types[0])

        # if the query asks for a class as subject or object
        # then use the class name as a variable name for the results
        subject_class = fact_pattern.get_subject_class()
        if subject_class:
            var_names_in_query.append((subject_class, "subject"))
        object_class = fact_pattern.get_object_class()
        if object_class:
            var_names_in_query.append((object_class, "object"))

        # execute the query
        collection2doc_ids = dict()
        # compute the list of substitutions for the variables
        var2subs = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        for result in query:
            document_ids = set(PredicationInvertedIndex.prepare_document_ids(result.document_ids))
            doc_col = result.document_collection

            # add the new documents to the existing collection, if existing
            if doc_col in collection2doc_ids:
                collection2doc_ids[doc_col].update(document_ids)
            else:
                collection2doc_ids[doc_col] = document_ids

            for var_name, position in var_names_in_query:
                sub_id, sub_type = None, None
                if position == 'subject':
                    sub_id, sub_type = result.subject_id, result.subject_type
                elif position == 'object':
                    sub_id, sub_type = result.object_id, result.object_type
                var2subs[var_name][doc_col][(sub_id, sub_type)].update(document_ids)
        return collection2doc_ids, var2subs

    @staticmethod
    def merge_var2subs(var2subs, var2subs_updates):
        for var_name in var2subs_updates:
            for doc_col in var2subs_updates[var_name]:
                for sub_key in var2subs_updates[var_name][doc_col]:
                    doc_ids = var2subs_updates[var_name][doc_col][sub_key]
                    var2subs[var_name][doc_col][sub_key].update(doc_ids)


    @staticmethod
    def merge_collection2docs(col2docs, col2docs_updates):
        for collection, document_ids in col2docs_updates.items():
            if collection in col2docs:
                col2docs[collection].update(document_ids)
            else:
                col2docs[collection] = document_ids

    @staticmethod
    def query_for_terms_in_query(graph_query: GraphQuery, document_collection_filter) -> {str: int}:
        # no entities -> no document filter
        if not graph_query.has_terms():
            return None

        session = SessionExtended.get()
        doc_col2valid_ids = {}
        for idx, term in enumerate(graph_query.terms):
            term_lower = term.lower().strip()
            q = session.query(TermInvertedIndex.document_collection, TermInvertedIndex.document_ids)
            q = q.filter(TermInvertedIndex.term == term_lower)

            if document_collection_filter:
                if len(document_collection_filter) == 1:
                    q = q.filter(TermInvertedIndex.document_collection == list(document_collection_filter)[0])
                else:
                    q = q.filter(TermInvertedIndex.document_collection.in_(document_collection_filter))

            collection2term_ids = {}
            for row in q:
                # interpret the string from db as a python string list
                if row.document_collection not in collection2term_ids:
                    collection2term_ids[row.document_collection] = ast.literal_eval(row.document_ids)
                else:
                    collection2term_ids[row.document_collection].update(ast.literal_eval(row.document_ids))

            for c in collection2term_ids:
                logging.debug(f'{len(collection2term_ids[c])} document ids for collection: "{c}" and term "{term}"')

            if idx == 0:
                # we are fine for now. First entity set resulted in doc_col2valid_ids
                doc_col2valid_ids = collection2term_ids
            else:
                # we are in the section iteration and must intersect the doc sets for the different terms
                for col, doc_ids in doc_col2valid_ids.items():
                    # only if the collection has at least a single document
                    if col in collection2term_ids:
                        doc_col2valid_ids[col].intersection_update(collection2term_ids[col])
                    else:
                        # no hits there
                        doc_col2valid_ids[col] = set()

        return doc_col2valid_ids

    @staticmethod
    def query_for_entities_in_query(graph_query: GraphQuery, document_collection_filter) -> {str: int}:
        # no entities -> no document filter
        if not graph_query.has_entities():
            return None

        session = SessionExtended.get()
        doc_col2valid_ids = {}
        for idx, entity_set in enumerate(graph_query.entity_sets):
            entity_ids = list([en.entity_id for en in entity_set])
            entity_types = list(set([en.entity_type for en in entity_set]))

            q = session.query(TagInvertedIndex.document_collection, TagInvertedIndex.document_ids)
            if document_collection_filter:
                if len(document_collection_filter) == 1:
                    q = q.filter(TagInvertedIndex.document_collection == list(document_collection_filter)[0])
                else:
                    q = q.filter(TagInvertedIndex.document_collection.in_(document_collection_filter))

            if len(entity_ids) == 1:
                # Check if we search with a variable
                if not entity_ids[0].startswith('?'):
                    q = q.filter(TagInvertedIndex.entity_id == entity_ids[0])
                else:
                    var_type = VAR_TYPE.search(entity_ids[0])
                    if var_type:
                        var_type = var_type.group(1)
                        logging.debug(f'Found variable for entity querying. Type is: {var_type}')
                        entity_types = [var_type]
            else:
                q = q.filter(TagInvertedIndex.entity_id.in_(entity_ids))

            if len(entity_types) == 1:
                q = q.filter(TagInvertedIndex.entity_type == entity_types[0])
            else:
                q = q.filter(TagInvertedIndex.entity_type.in_(entity_types))

            e_doc_col2valid_ids = {}
            for row in q:
                # interpret the string from db as a python string list
                if row.document_collection not in e_doc_col2valid_ids:
                    e_doc_col2valid_ids[row.document_collection] = set(ast.literal_eval(row.document_ids))
                else:
                    e_doc_col2valid_ids[row.document_collection].update(set(ast.literal_eval(row.document_ids)))

            if idx == 0:
                # we are fine for now. First entity set resulted in doc_col2valid_ids
                doc_col2valid_ids = e_doc_col2valid_ids
            else:
                # we are in the section iteration and must intersect the doc sets for the different entity sets
                for col, doc_ids in doc_col2valid_ids.items():
                    if col in e_doc_col2valid_ids:
                        doc_col2valid_ids[col].intersection_update(e_doc_col2valid_ids[col])
                    else:
                        # no hits there
                        doc_col2valid_ids[col] = set()

        return doc_col2valid_ids

    @staticmethod
    def process_query_without_statements(graph_query: GraphQuery, document_collection_filter: Set[str] = None,
                                         load_document_metadata: bool = True) -> List[QueryDocumentResult]:
        logging.debug('Process query without statements...')
        collection2valid_doc_ids = {}
        # Query for terms and entities
        if graph_query.has_terms():
            logging.debug(f'Compute document ids for terms: {graph_query.terms}')
            term_collection2ids = QueryEngine.query_for_terms_in_query(graph_query, document_collection_filter)
            collection2valid_doc_ids = term_collection2ids

        if graph_query.has_entities():
            logging.debug(f'Compute document ids for entities: {graph_query.entity_sets}')
            entity_collection2ids = QueryEngine.query_for_entities_in_query(graph_query, document_collection_filter)
            if not graph_query.has_terms():
                collection2valid_doc_ids = entity_collection2ids
            else:
                # we know that the query has entities and terms
                # now intersect the term document sets with entity ids
                for d_col, d_ids in collection2valid_doc_ids.items():
                    if d_col in entity_collection2ids:
                        d_ids.intersection_update(entity_collection2ids[d_col])
                    else:
                        # no entity collection match
                        d_ids = set()
                    logging.debug(f'After filtering with entities: {len(d_ids)} doc_ids left')

        # No variables are used in the query
        query_results = []
        for d_col, d_ids in collection2valid_doc_ids.items():
            for d_id in d_ids:
                query_results.append(QueryDocumentResult(int(d_id), title="", authors="", journals="",
                                                         publication_year=0, publication_month=0,
                                                         var2substitution={}, confidence=0.0,
                                                         position2provenance_ids={},
                                                         org_document_id=None, doi=None,
                                                         document_collection=d_col, document_classes=None))
        if load_document_metadata:
            query_results = QueryEngine.enrich_document_results_with_metadata(query_results, collection2valid_doc_ids)

        logging.debug(f'{len(query_results)} results computed')
        return query_results

    @staticmethod
    def process_query_with_expansion(graph_query: GraphQuery, document_collection_filter: Set[str] = None,
                                     load_document_metadata=True) \
            -> List[QueryDocumentResult]:
        """
        Computes a GraphQuery
        The query will automatically be expanded and optimized
        :param graph_query: a graph query object
        :param document_collection_filter: only keep extraction from these document collections
        :param load_document_metadata: if true metadata will be queried for the retrieved documents
        :return: a list of QueryDocumentResults
        """
        start_time = datetime.now()

        if not graph_query.has_statements() and (graph_query.has_entities() or graph_query.has_terms()):
            return QueryEngine.process_query_without_statements(graph_query, document_collection_filter,
                                                                load_document_metadata)

        graph_query = QueryOptimizer.optimize_query(graph_query)
        if not graph_query:
            logging.debug('Query will not yield results - returning empty list')
            return []

        collection2valid_doc_ids = defaultdict(set)
        collection2valid_subs = {}

        logging.debug(f'Executing query {graph_query}...')
        for idx, fact_pattern in enumerate(graph_query):
            collection2doc_ids, var2subs = QueryEngine.query_inverted_index_for_fact_pattern(fact_pattern,
                                                                                        document_collection_filter=document_collection_filter)
            # must the fact pattern be expanded?
            for e_fp in QueryExpander.expand_fact_pattern(fact_pattern):
                logging.debug(f'Expand {fact_pattern} to {e_fp}')
                collection2docs_expanded, var2subs_ex = QueryEngine.query_inverted_index_for_fact_pattern(e_fp,
                                                                                       document_collection_filter=document_collection_filter)
                QueryEngine.merge_var2subs(var2subs, var2subs_ex)
                QueryEngine.merge_collection2docs(collection2doc_ids, collection2docs_expanded)

            # Next compute the intersection of document ids with prior result sets
            if idx == 0:
                collection2valid_doc_ids = collection2doc_ids
            else:
                for d_col in collection2valid_doc_ids:
                    if d_col in collection2doc_ids:
                        collection2valid_doc_ids[d_col] = collection2valid_doc_ids[d_col].intersection(collection2doc_ids[d_col])
                    else:
                        collection2valid_doc_ids[d_col] = set()

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

        logging.debug(f'Query computed in {datetime.now() - start_time}s')
        # Construct the results
        # query document titles
        query_results = []

        et_query_start = datetime.now()
        # Query for terms and entities
        term_collection2ids = QueryEngine.query_for_terms_in_query(graph_query, document_collection_filter)
        entity_collection2ids = QueryEngine.query_for_entities_in_query(graph_query, document_collection_filter)
        # Apply filter
        if term_collection2ids:
            for d_col, d_ids in collection2valid_doc_ids.items():
                if d_col in term_collection2ids:
                    d_ids.intersection_update(term_collection2ids[d_col])
                else:
                    # no term collection match
                    d_ids = set()
                logging.debug(f'After filtering with terms: {len(d_ids)} doc_ids left')
        # Apply filter
        if entity_collection2ids:
            for d_col, d_ids in collection2valid_doc_ids.items():
                if d_col in entity_collection2ids:
                    d_ids.intersection_update(entity_collection2ids[d_col])
                else:
                    # no entity collection match
                    d_ids = set()
                logging.debug(f'After filtering with entities: {len(d_ids)} doc_ids left')

        logging.debug(f'Entity and term filter computed in {datetime.now() - et_query_start}s')

        # No variables are used in the query
        if len(collection2valid_subs) == 0:
            for d_col, d_ids in collection2valid_doc_ids.items():
                for d_id in d_ids:
                    query_results.append(QueryDocumentResult(int(d_id), title="", authors="", journals="",
                                                             publication_year=0, publication_month=0,
                                                             var2substitution={}, confidence=0.0,
                                                             position2provenance_ids={},
                                                             org_document_id=None, doi=None,
                                                             document_collection=d_col, document_classes=None))
        else:
            for d_col, d_ids in collection2valid_doc_ids.items():
                # Todo: Hack
                if len(d_ids) > QUERY_DOCUMENT_LIMIT:
                    logging.warning(f'Query limit was hit: {len(d_ids)} (Limit: {QUERY_DOCUMENT_LIMIT}')
                    sorted_d_ids = sorted(list(list(d_ids)), reverse=True)
                    logging.warning(f'Only considering the latest {QUERY_DOCUMENT_LIMIT} document ids')
                    sorted_d_ids = sorted_d_ids[:QUERY_DOCUMENT_LIMIT]
                    d_ids = set(sorted_d_ids)

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

                        query_results.append(QueryDocumentResult(int(d_id), title="", authors="", journals="",
                                                                 publication_year=0, publication_month=0,
                                                                 var2substitution=var2sub_for_doc,
                                                                 confidence=0.0,
                                                                 position2provenance_ids={},
                                                                 org_document_id=None, doi=None,
                                                                 document_collection=d_col,
                                                                 document_classes=None))

        # Apply metadata filter in the end
        if load_document_metadata:
            query_results = QueryEngine.enrich_document_results_with_metadata(query_results, collection2valid_doc_ids)

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
