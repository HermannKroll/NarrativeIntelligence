import itertools
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import List

from sqlalchemy import func, and_
from sqlalchemy.orm import aliased

from narraint.backend.models import Document, Predication, Sentence
from narraint.backend.database import Session
from sqlalchemy.dialects import postgresql

from narraint.entity.entity import Entity
from narraint.queryengine.expander import QueryExpander
from narraint.queryengine.logger import QueryLogger
from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import DO_NOT_CARE_PREDICATE, SYMMETRIC_PREDICATES, \
    PREDICATE_EXPANSION, should_perform_like_search_for_entity, ENTITY_TYPE_EXPANSION, ENTITY_TYPE_VARIABLE, VAR_NAME, \
    VAR_TYPE, VAR_TYPE_PREDICATE, QUERY_LIMIT
from narraint.queryengine.result import QueryFactExplanation, QueryDocumentResult, QueryEntitySubstitution


class QueryEngine:

    def __init__(self):
        self.query_logger = QueryLogger()

    def __construct_query(self, session, query_patterns: [(Entity, str, Entity)], doc_collection, extraction_type=None,
                          likesearch=True, document_ids=None):
        var_names = []
        var_dict = {}
        if len(query_patterns) == 0:
            raise ValueError('Query needs to contain at least a single fact pattern')

        predication_aliases = []
        for idx, _ in enumerate(query_patterns):
            predication_aliases.append(aliased(Predication, name='P{}'.format(idx)))

        projection_list = []
        for idx, p in enumerate(predication_aliases):
            # the first entry needs to project the document id
            if idx == 0:
                projection_list.extend([p.document_id, p.subject_id, p.subject_str, p.subject_type,
                                        p.predicate_canonicalized, p.object_id, p.object_str, p.object_type,
                                        p.confidence, p.predicate, p.sentence_id])
            else:
                projection_list.extend([p.subject_id, p.subject_str, p.subject_type, p.predicate_canonicalized,
                                        p.object_id, p.object_str, p.object_type, p.confidence, p.predicate,
                                        p.sentence_id])

        pred0 = predication_aliases[0]
        query = session.query(*projection_list)
        query = query.filter(pred0.document_collection == doc_collection)

        # just get documents which are contained here
        if document_ids:
            query = query.filter(pred0.document_id.in_(document_ids))
        if extraction_type:
            query = query.filter(pred0.extraction_type == extraction_type)
        for pred in predication_aliases[1:]:
            query = query.filter(pred.document_id == pred0.document_id)
            query = query.filter(pred.document_collection == doc_collection)
            if extraction_type:
                query = query.filter(pred.extraction_type == extraction_type)

        for idx, (subj, p, obj) in enumerate(query_patterns):
            s, s_t = subj.entity_id, subj.entity_type
            o, o_t = obj.entity_id, obj.entity_type
            pred = predication_aliases[idx]

            # variable in pattern
            if s.startswith('?') or p.startswith('?') or o.startswith('?'):
                # the idea of the following blocks is as follows:
                # if x ( here subject, predicate or object) is not a var -> just add a where condition
                # if x is a variable
                # check if x already occurred -> yes join both aliased predication together
                # if x is new, just add it as the last predication of the variable
                if not s.startswith('?'):
                    if likesearch and should_perform_like_search_for_entity(s, s_t):
                        query = query.filter(and_(pred.subject_id.like('{}%'.format(s)), pred.subject_type == s_t))
                    else:
                        query = query.filter(pred.subject_id == s)
                else:
                    var_name = VAR_NAME.search(s)
                    if not var_name:
                        raise ValueError('Variable name does not match regex: {}'.format(s))
                    var_name = var_name.group(1)
                    var_type = VAR_TYPE.search(s)
                    if var_type:
                        var_type = var_type.group(1)
                        if var_type in ENTITY_TYPE_EXPANSION:
                            query = query.filter(pred.subject_type.in_(ENTITY_TYPE_EXPANSION[var_type]))
                        else:
                            query = query.filter(pred.subject_type == var_type)
                    if var_name not in var_dict:
                        var_names.append((var_name, 'subject', idx))
                        var_dict[var_name] = (pred, 'subject')
                    else:
                        last_pred, t = var_dict[var_name]
                        if t == 'subject':
                            query = query.filter(pred.subject_id == last_pred.subject_id)
                        elif t == 'object':
                            query = query.filter(pred.subject_id == last_pred.object_id)
                        else:
                            ValueError('Variable cannot be used as predicate and subject / object.')
                if not o.startswith('?'):
                    if likesearch and should_perform_like_search_for_entity(o, o_t):
                        query = query.filter(and_(pred.object_id.like('{}%'.format(o)), pred.object_type == o_t))
                    else:
                        query = query.filter(pred.object_id == o)
                else:
                    var_name = VAR_NAME.search(o)
                    if not var_name:
                        raise ValueError('Variable name does not match regex: {}'.format(o))
                    var_name = var_name.group(1)
                    var_type = VAR_TYPE.search(o)
                    if var_type:
                        var_type = var_type.group(1)
                        if var_type in ENTITY_TYPE_EXPANSION:
                            query = query.filter(pred.object_type.in_(ENTITY_TYPE_EXPANSION[var_type]))
                        else:
                            query = query.filter(pred.object_type == var_type)
                    if var_name not in var_dict:
                        var_names.append((var_name, 'object', idx))
                        var_dict[var_name] = (pred, 'object')
                    else:
                        last_pred, t = var_dict[var_name]
                        if t == 'object':
                            query = query.filter(pred.object_id == last_pred.object_id)
                        elif t == 'subject':
                            query = query.filter(pred.object_id == last_pred.subject_id)
                        else:
                            raise ValueError('Variable cannot be used as predicate and subject / object.')
                if p == DO_NOT_CARE_PREDICATE:
                    query = query.filter(pred.predicate_canonicalized.isnot(None))
                elif not p.startswith('?'):
                    query = query.filter(pred.predicate_canonicalized == p)
                else:
                    query = query.filter(pred.predicate_canonicalized.isnot(None))
                    var_type = VAR_TYPE_PREDICATE.search(p)
                    if var_type:
                        query = query.filter(pred.subject_type == var_type.group(1))
                        query = query.filter(pred.object_type == var_type.group(2))
                    if p not in var_dict:
                        var_names.append((p, 'predicate', idx))
                        var_dict[p] = (pred, 'predicate')
                    else:
                        last_pred, t = var_dict[p]
                        if t == 'predicate':
                            query = query.filter(pred.predicate_canonicalized == last_pred.predicate_canonicalized)
                        else:
                            raise ValueError('Variable cannot be used as predicate and subject / object.')
            else:
                if likesearch and should_perform_like_search_for_entity(s, s_t):
                    query = query.filter(and_(pred.subject_id.like('{}%'.format(s)), pred.subject_type == s_t))
                else:
                    query = query.filter(pred.subject_id == s)
                if likesearch and should_perform_like_search_for_entity(o, o_t):
                    query = query.filter(and_(pred.object_id.like('{}%'.format(o)), pred.object_type == o_t))
                else:
                    query = query.filter(pred.object_id == o)
                if p == DO_NOT_CARE_PREDICATE:
                    query = query.filter(pred.predicate_canonicalized.isnot(None))
                else:
                    query = query.filter(pred.predicate_canonicalized == p)

        # order by document id descending and limit results to 100
        query = query.order_by(func.random()).limit(QUERY_LIMIT)
        return query, var_names

    def query_with_graph_query(self, query_patterns: [(Entity, str, Entity)], doc_collection, extraction_type=None,
                               keyword_query='', query_titles_and_sentences=True, likesearch=True, document_ids=None):
        if len(query_patterns) == 0:
            raise ValueError('graph query must contain at least one fact')

        session = Session.get()
        query, var_info = self.__construct_query(session, query_patterns, doc_collection, extraction_type, likesearch,
                                                 document_ids)

        #  sql_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=postgresql.dialect()))
        logging.debug('executing sql statement for: {}'.format(query_patterns))
        # logging.debug('sql statement is: {}'.format(sql_query))
        var_names = []
        for v, _, _ in var_info:
            var_names.append(v)

        doc_ids = set()
        sentence_ids = set()
        doc2result = {}
        result_count = 0
        for r in session.execute(query):
            result_count += 1
            # extract var substitutions for pmid
            var2sub = {}
            for v, t, pred_pos in var_info:
                offset = 1 + pred_pos * 10

                if t == 'subject':
                    # it's ent_str, ent_id, ent_type
                    var2sub[v] = QueryEntitySubstitution(r[offset + 1], r[offset], r[offset + 2])
                elif t == 'object':
                    # it's ent_str, ent_id, ent_type
                    var2sub[v] = QueryEntitySubstitution(r[offset + 5], r[offset + 4], r[offset + 6])
                elif t == 'predicate':
                    var2sub[v] = QueryEntitySubstitution(r[offset + 3], 'predicate', 'predicate')
                else:
                    raise ValueError('Unknown position in query projection')

            # extract confidence & explanation for facts
            explanations = []
            conf = 0
            for i in range(0, len(query_patterns)):
                offset = 1 + i * 10
                subject_str = r[offset + 1]
                object_str = r[offset + 5]
                predicate_canonicalized = r[offset + 3]
                predicate = r[offset + 8]
                sentence_id = int(r[offset + 9])
                sentence_ids.add(sentence_id)
                explanations.append(
                    QueryFactExplanation(i, sentence_id, predicate, predicate_canonicalized, subject_str,
                                         object_str))
                if r[offset + 7]:
                    conf += float(r[offset + 7])
                else:
                    conf += 0.0
            # create query result
            doc_id = int(r[0])
            doc_ids.add(doc_id)

            # each document id + the variable substitution forms a unique document result
            var2sub_set = set()
            for k, v in var2sub.items():
                var2sub_set.add('{}:{}'.format(k, v.entity_id))
            key = (doc_id, frozenset(var2sub_set))
            if key not in doc2result:
                doc2result[key] = QueryDocumentResult(doc_id, r[1], var2sub, conf, explanations)
            else:
                for e in explanations:
                    doc2result[key].integrate_explanation(e)

        if query_titles_and_sentences:
            doc2titles, id2sentences = self.query_titles_and_sentences_for_doc_ids(doc_ids, sentence_ids,
                                                                                   doc_collection)
            # Replace all previously assigned empty titles and sentence ids by document titles and sentence ids
            for (doc_id, var2sub_set), result in doc2result.items():
                result.title = doc2titles[doc_id]
                for e in result.explanations:
                    e.sentence = id2sentences[e.sentence]

        results = list(doc2result.values())

        # logging.debug('{} database tuples retrieved'.format(result_count))
        logging.debug('{} distinct doc ids retrieved'.format(len(doc_ids)))
        # logging.debug("{} results with doc ids: {}".format(len(results), doc_ids))

        query_hit_limit = False
        if result_count >= QUERY_LIMIT:
            logging.debug(f'{result_count} hit query limit')
            query_hit_limit = True

        return results, query_hit_limit

    def query_titles_and_sentences_for_doc_ids(self, doc_ids, sentence_ids, document_collection):
        """
        Query the titles and sentences for a set of doc ids and sentence ids
        :param doc_ids: a set of doc ids
        :param sentence_ids: a set of sentence ids
        :param document_collection: the corresponding document collection
        :return: dict mapping docids to titles, dict mapping sentence ids to sentence texts
        """
        session = Session.get()
        # Query the document titles
        q_titles = session.query(Document.id, Document.title).filter(Document.collection == document_collection)
        q_titles = q_titles.filter(Document.id.in_(doc_ids))
        doc2titles = {}
        for r in q_titles:
            title = r[1]
            if len(title) > 500:
                logging.debug('Large title detected: {}'.format(r[0]))
                title = title[0:500]
            doc2titles[int(r[0])] = title

        # Query the sentences
        q_sentences = session.query(Sentence.id, Sentence.text).filter(Sentence.id.in_(sentence_ids))
        id2sentences = {}
        for r in q_sentences:
            sent = r[1]
            if len(sent) > 1500:
                logging.debug('long sentence detected for: {}'.format(r[0]))
                sent = '{}[...]'.format(sent[0:1500])
            id2sentences[int(r[0])] = sent

        return doc2titles, id2sentences

    def _merge_results(self, results: [QueryDocumentResult]) -> [QueryDocumentResult]:
        """
        Merges a list of document results and eliminates duplicated documents
        :param results: a list of QueryDocumentResult
        :return: a list of unique QueryDocumentResult
        """
        result_index = {}
        unique_results = []
        for r in results:
            if r.document_id in result_index:
                is_new_document = True
                for existing in result_index[r.document_id]:
                    if existing == r:
                        is_new_document = False
                        break
                if is_new_document:
                    result_index[r.document_id].append(r)
                    unique_results.append(r)
            else:
                result_index[r.document_id] = [r]
                unique_results.append(r)
        return unique_results

    def process_query_with_expansion(self, graph_query: GraphQuery, document_collection, extraction_type=None,
                                     query="", likesearch=True):
        """
        Executes the query fact patterns as a SQL query and collects all results
        Expands the query automatically, if e.g. a MeSH descriptor has several tree numbers
        :param graph_query: a graph query object
        :param document_collection: the document collection to query
        :param extraction_type: the extraction type to query
        :param query: the query as the input string for logging
        :param likesearch: performs like searches for subjects and objects
        :return: a list of QueryDocumentResults, if the query limit was hit
        """
        start_time = datetime.now()
        query_limit_hit = False
        # The query expander will generate a list of queries to execute
        # Each query consists of a set of facts
        # The results of each fact pattern will be executed as being connected by an OR
        expanded_queries = QueryExpander.expand_query(graph_query)
        # optimize each query
        # each query is a set of fact pattern which should be executed as OR (so set and_mod to false here)
        optimized_expanded_queries = list([QueryOptimizer.optimize_query(q, and_mod=False) for q in expanded_queries])
        # remove none objects
        optimized_expanded_queries = [q for q in optimized_expanded_queries if q]
        if len(optimized_expanded_queries) == 0:
            logging.debug('Query wont yield results - returning empty list')
            return [], False

        queries_to_execute = sum([len(q.fact_patterns) for q in optimized_expanded_queries])
        logging.debug('The query will be expanded into {} queries'.format(queries_to_execute))

        if len(optimized_expanded_queries) > 1 or len(optimized_expanded_queries[0].fact_patterns) > 1:
            # database join for fact patterns seems to be very slow
            # Idea: execute after each other and join results in memory
            temp_results = defaultdict(list)
            valid_doc_ids = set()
            valid_var_subs = defaultdict(set)
            for idx, expanded_query in enumerate(optimized_expanded_queries):
                part_result = []

                if idx == 0:
                    document_id_filter = None
                else:
                    document_id_filter = valid_doc_ids
                for q_fp in expanded_query.fact_patterns:
                    if len(q_fp.subjects) > 1 or len(q_fp.objects) > 1:
                        raise ValueError('Can only execute query fact patterns with a single subject and object')
                    query_pattern = [(q_fp.subjects[0], q_fp.predicate, q_fp.objects[0])]
                    query_result, hit_limit = self.query_with_graph_query(query_pattern,
                                                                          document_collection,
                                                                          extraction_type, query,
                                                                          query_titles_and_sentences=False,
                                                                          likesearch=likesearch,
                                                                          document_ids=document_id_filter)
                    part_result.extend(query_result)
                    if hit_limit:
                        query_limit_hit = True
                results = self._merge_results(part_result)
                new_doc_ids = set()
                new_var_subs = defaultdict(set)
                for r in results:
                    # update the explanation position
                    for e in r.explanations:
                        e.position = idx
                    for var, var_sub in r.var2substitution.items():
                        new_var_subs[var].add((r.document_id, var_sub.entity_id, var_sub.entity_type))
                    temp_results[r.document_id].append(r)

                    new_doc_ids.add(r.document_id)
                if idx == 0:
                    valid_var_subs = new_var_subs
                    valid_doc_ids = new_doc_ids
                else:
                    # compute intersection to ensure that both required facts are mentioned in both documents
                    for var in new_var_subs:
                        if var in valid_var_subs:
                            # if there are already substitutions for a specific variable -> intersect
                            valid_var_subs[var] = valid_var_subs[var].intersection(new_var_subs[var])
                        else:
                            # its a new variable which is not known now
                            valid_var_subs[var] = new_var_subs[var]
                    valid_doc_ids = valid_doc_ids.intersection(new_doc_ids)

            if len(valid_var_subs) == 0:
                # do not check any variable
                doc2result = {}
                for doc_id, result_list in temp_results.items():
                    if doc_id in valid_doc_ids:
                        for r in result_list:
                            if doc_id not in doc2result:
                                doc2result[doc_id] = r
                            else:
                                for e in r.explanations:
                                    doc2result[doc_id].integrate_explanation(e)
                doc_results = doc2result.values()
            else:
                # check compatibility between variable substitutions
                doc2valid_var_sub = defaultdict(lambda: defaultdict(set))
                doc2doc_results_without_var = defaultdict(list)
                doc_and_var_sub2results = defaultdict(list)
                valid_doc_ids_final = set()
                for doc_id, result_list in temp_results.items():
                    if doc_id in valid_doc_ids:
                        for r in result_list:
                            for var, var_sub in r.var2substitution.items():
                                if (r.document_id, var_sub.entity_id, var_sub.entity_type) in valid_var_subs[var]:
                                    v_key = (var_sub.entity_id, var_sub.entity_type)
                                    doc2valid_var_sub[doc_id][var].add(v_key)
                                    v_sub_key = (doc_id, var, var_sub.entity_id, var_sub.entity_type)
                                    doc_and_var_sub2results[v_sub_key].append(r)
                                    valid_doc_ids_final.add(doc_id)
                            if len(r.var2substitution) == 0:
                                doc2doc_results_without_var[doc_id].append(r)

                var_names = sorted(list(valid_var_subs.keys()))
                doc_results = []
                for doc_id in valid_doc_ids_final:
                    subs_for_document = []
                    for var_name in var_names:
                        subs_for_document.append(doc2valid_var_sub[doc_id][var_name])

                    sub_combinations_for_document = list(itertools.product(*subs_for_document))
                    for combination in sub_combinations_for_document:
                        doc_result_for_combi = None
                        for idx, (var_name, var_sub) in enumerate(zip(var_names, combination)):
                            v_sub_key = (doc_id, var_name, var_sub[0], var_sub[1])
                            for doc_result in doc_and_var_sub2results[v_sub_key]:
                                if not doc_result_for_combi:
                                    doc_result_for_combi = doc_result
                                else:
                                    doc_result_for_combi.var2substitution.update(doc_result.var2substitution)
                                    for e in doc_result.explanations:
                                        doc_result_for_combi.integrate_explanation(e)
                        for doc_result in doc2doc_results_without_var[doc_id]:
                            if not doc_result_for_combi:
                                doc_result_for_combi = doc_result
                            else:
                                for e in doc_result.explanations:
                                    doc_result_for_combi.integrate_explanation(e)
                        doc_results.append(doc_result_for_combi)

            results = doc_results
        else:
            if len(optimized_expanded_queries) > 1 or len(optimized_expanded_queries[0].fact_patterns) > 1:
                raise ValueError('There are multiple queries to execute... they should be handled elsewhere')
            graph_query = optimized_expanded_queries[0]
            graph_patterns = []
            for fp in graph_query.fact_patterns:
                if len(fp.subjects) > 1 or len(fp.objects) > 1:
                    raise ValueError('Graph Patterns should only have a single entity as subject or object: {}'
                                     .format(fp))
                graph_patterns.append((fp.subjects[0], fp.predicate, fp.objects[0]))
            results, hit_limit = self.query_with_graph_query(graph_patterns, document_collection,
                                                             extraction_type, query, query_titles_and_sentences=False,
                                                             likesearch=likesearch)
            if hit_limit:
                query_limit_hit = True

        # Replace all empty titles and sentence ids by the corresponding titles and explanations
        doc_ids = set()
        sentence_ids = set()
        for r in results:
            doc_ids.add(r.document_id)
            for e in r.explanations:
                sentence_ids.add(e.sentence)

        doc2titles, id2sentences = self.query_titles_and_sentences_for_doc_ids(doc_ids, sentence_ids,
                                                                               document_collection)
        # Replace all previously assigned empty titles and sentence ids by document titles and sentence ids
        for result in results:
            result.title = doc2titles[result.document_id]
            for e in result.explanations:
                try:
                    e.sentence = id2sentences[e.sentence]
                except KeyError:
                    pass

        time_needed = datetime.now() - start_time
        self.query_logger.write_log(time_needed, document_collection, graph_query, len(doc_ids))

        return sorted(results, key=lambda d: d.document_id, reverse=True), query_limit_hit

    @staticmethod
    def query_predicates(collection=None):
        session = Session.get()
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
        session = Session.get()
        query_subjects = session.query(Predication.subject_id, Predication.subject_str,
                                       Predication.subject_type).distinct()
        query_subjects = query_subjects.filter(Predication.predicate_canonicalized.isnot(None))
        query_objects = session.query(Predication.object_id, Predication.object_str, Predication.object_type).distinct()
        query_objects = query_objects.filter(Predication.predicate_canonicalized.isnot(None))
        query = query_subjects.union(query_objects).distinct()

        entities = set()
        start_time = datetime.now()
        for r in session.execute(query):
            ent_id, ent_str, ent_type = r[0], r[1], r[2]
            entities.add((ent_id, ent_str, ent_type))

        logging.info('{} entities queried in {}s'.format(len(entities), datetime.now() - start_time))
        return entities
