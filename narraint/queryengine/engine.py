import itertools
import logging
import re
from datetime import datetime

from sqlalchemy.orm import aliased

from narraint.backend.models import Document, Predication
from narraint.backend.database import Session
from sqlalchemy.dialects import postgresql

from narraint.queryengine.logger import QueryLogger
from narraint.queryengine.result import QueryFactExplanation, QueryDocumentResult, QueryEntitySubstitution

QUERY_LIMIT = 10000
VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE = re.compile(r'\((\w+)\)')
VAR_TYPE_PREDICATE = re.compile(r'\((\w+),(\w+)\)')
DO_NOT_CARE_PREDICATE = 'associated'


class QueryEngine:

    def __init__(self):
        self.query_logger = QueryLogger()

    def __construct_query(self, session, graph_query, doc_collection, extraction_type):
        var_names = []
        var_dict = {}

        document = aliased(Document, name='D')
        predication_aliases = []
        for idx, _ in enumerate(graph_query):
            predication_aliases.append(aliased(Predication, name='P{}'.format(idx)))

        projection_list = [document.id, document.title]
        for p in predication_aliases:
            projection_list.extend([p.subject_id, p.subject_str, p.subject_type, p.predicate_canonicalized, p.object_id,
                                    p.object_str, p.object_type, p.confidence, p.predicate_cleaned, p.sentence])

        query = session.query(*projection_list).distinct()
        query = query.filter(document.collection == doc_collection)
        for pred in predication_aliases:
            query = query.filter(document.id == pred.document_id)

        for idx, (s, s_t, p, o, o_t) in enumerate(graph_query):
            pred = predication_aliases[idx]
            query = query.filter(pred.document_collection == doc_collection)
            query = query.filter(pred.extraction_type == extraction_type)

            # variable in pattern
            if s.startswith('?') or p.startswith('?') or o.startswith('?'):
                # the idea of the following blocks is as follows:
                # if x ( here subject, predicate or object) is not a var -> just add a where condition
                # if x is a variable
                # check if x already occurred -> yes join both aliased predication together
                # if x is new, just add it as the last predication of the variable
                if not s.startswith('?'):
                    query = query.filter(pred.subject_id.like('{}%'.format(s)))
                else:
                    var_name = VAR_NAME.search(s)
                    if not var_name:
                        raise ValueError('Variable name does not match regex: {}'.format(s))
                    var_name = var_name.group(1)
                    var_type = VAR_TYPE.search(s)
                    if var_type:
                        query = query.filter(pred.subject_type == var_type.group(1))
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
                    query = query.filter(pred.object_id.like('{}%'.format(o)))
                else:
                    var_name = VAR_NAME.search(o)
                    if not var_name:
                        raise ValueError('Variable name does not match regex: {}'.format(o))
                    var_name = var_name.group(1)
                    var_type = VAR_TYPE.search(o)
                    if var_type:
                        query = query.filter(pred.object_type == var_type.group(1))
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
                if p == DO_NOT_CARE_PREDICATE:
                    query = query.filter(pred.subject_id.like('{}%'.format(s)), pred.object_id.like('{}%'.format(o)))
                    query = query.filter(pred.predicate_canonicalized.isnot(None))
                else:
                    query = query.filter(pred.subject_id.like('{}%'.format(s)), pred.object_id.like('{}%'.format(o)),
                                         pred.predicate_canonicalized == p)

        # order by document id descending and limit results to 100
        query = query.order_by(document.id.desc()).limit(QUERY_LIMIT)

        return query, var_names

    def query_with_graph_query(self, graph_query, doc_collection, extraction_type, keyword_query=''):
        if len(graph_query) == 0:
            raise ValueError('graph query must contain at least one fact')

        session = Session.get()
        query, var_info = self.__construct_query(session, graph_query, doc_collection, extraction_type)

        sql_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=postgresql.dialect()))
        logging.debug('executing sql statement: {}'.format(sql_query))
        var_names = []
        for v, _, _ in var_info:
            var_names.append(v)

        start = datetime.now()
        doc_ids = set()
        doc2result = {}
        for r in session.execute(query):
            # extract var substitutions for pmid
            var2sub = {}
            for v, t, pred_pos in var_info:
                offset = 2 + pred_pos * 10

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
            for i in range(0, len(graph_query)):
                offset = 2 + i * 10
                subject_str = r[offset + 1]
                object_str = r[offset + 5]
                predicate_canonicalized = r[offset + 3]
                predicate = r[offset + 8]
                sentence = r[offset + 9]
                explanations.append(QueryFactExplanation(i, sentence, predicate, predicate_canonicalized, subject_str,
                                                         object_str))
                conf += float(r[offset + 7])
            # create query result
            doc_id = r[0]
            doc_ids.add(doc_id)

            # each document id + the variable substitution forms a unique document result
            var2sub_set = set()
            for k, v in var2sub:
                var2sub_set.add('{}:{}'.format(k, v))
            key = (doc_id, frozenset(var2sub_set))
            if key not in doc2result:
                doc2result[key] = QueryDocumentResult(doc_id, r[1], var2sub, conf, explanations)
            else:
                for e in explanations:
                    doc2result[key].integrate_explanation(e)

        results = list(doc2result.values())

        time_needed = datetime.now() - start
        self.query_logger.write_log(time_needed, 'openie', keyword_query, graph_query,
                                    sql_query.replace('\n', ' '), doc_ids)
        logging.debug('{} distinct doc ids retrieved'.format(len(doc_ids)))
        logging.debug("{} results with doc ids: {}".format(len(results), doc_ids))
        return results

    def _compute_entity_list(self, entity, entity_type):
        """
        Transforms an entity and entity type into a list
        If the entity is a list of tree numbers nothing happens
        else the entity will be packed into a list
        :param entity: an entity id
        :param entity_type: the entity type
        :return: returns the entity id packed in a list
        """
        if entity_type == 'MESH_ONTOLOGY':
            # it is already a list of tree numbers
            return entity
        else:
            return [entity]

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

    def process_query_with_expansion(self, query_fact_patterns, document_collection, extraction_type, query):
        """
        Executes the query fact patterns as a SQL query and collects all results
        Expands the query automatically, if e.g. a MeSH descriptor has several tree numbers
        :param query_fact_patterns: a list of query fact patterns
        :param document_collection: the document collection to query
        :param extraction_type: the extraction type to query
        :param query: the query as the input string for logging
        :return: a list of QueryDocumentResults
        """
        query_fact_patterns_expanded = []
        expand_query = False
        for idx, qp in enumerate(query_fact_patterns):
            exp_cond1 = len(qp[0]) > 1
            exp_cond2 = len(qp[3]) > 1

            if exp_cond1 or exp_cond2:
                expand_query = True
                subj_entities = self._compute_entity_list(qp[0], qp[1])
                subj_type = qp[1]
                predicates = [qp[2]]
                obj_entities = self._compute_entity_list(qp[3], qp[4])
                obj_type = qp[4]
                cross_product = list(
                    itertools.product(subj_entities, [subj_type], predicates, obj_entities, [obj_type]))
                query_fact_patterns_expanded.append(cross_product)
            else:
                query_fact_patterns_expanded.append(qp)

        if expand_query:
            query_fact_patterns_expanded = list(itertools.product(*query_fact_patterns_expanded))
            logging.info('The query will be expanded into {} queries'.format(len(query_fact_patterns_expanded)))
            part_result = []
            for query_fact_patterns in query_fact_patterns_expanded:
                part_result.extend(self.query_with_graph_query(list(query_fact_patterns), document_collection,
                                                               extraction_type, query))
            results = self._merge_results(part_result)

        else:
            results = self.query_with_graph_query(query_fact_patterns_expanded, document_collection,
                                                  extraction_type, query)
        return results

    @staticmethod
    def query_predicates_cleaned(collection=None):
        session = Session.get()
        if not collection:
            query = session.query(Predication.predicate_cleaned.distinct()). \
                filter(Predication.predicate_cleaned.isnot(None))
        else:
            query = session.query(Predication.predicate_cleaned.distinct()). \
                filter(Predication.predicate_cleaned.isnot(None)). \
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
        query_objects = session.query(Predication.object_id, Predication.object_str, Predication.object_type).distinct()
        query = query_subjects.union(query_objects).distinct()

        entities = set()
        start_time = datetime.now()
        for r in session.execute(query):
            ent_id, ent_str, ent_type = r[0], r[1], r[2]
            entities.add((ent_id, ent_str, ent_type))

        logging.info('{} entities queried in {}s'.format(len(entities), datetime.now() - start_time))
        return entities
