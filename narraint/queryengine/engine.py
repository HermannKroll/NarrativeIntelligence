import logging
import re
from datetime import datetime
from collections import namedtuple

from sqlalchemy.orm import aliased

from narraint.backend.models import Document, Predication
from narraint.backend.database import Session
from sqlalchemy.dialects import postgresql

from narraint.queryengine.logger import QueryLogger
from narraint.queryengine.result import QueryFactExplanation, QueryResult, QueryResultAggregate

QUERY_LIMIT = 10000
VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE = re.compile(r'\((\w+)\)')
VAR_TYPE_PREDICATE = re.compile(r'\((\w+),(\w+)\)')
SUBSTITUTION = namedtuple('Substitution', ['entity_str', 'entity_id', 'entity_type'])


class QueryEngine:

    def __init__(self):
        self.query_logger = QueryLogger()

    def __construct_query(self, session, graph_query, doc_collection):
        var_names = []
        var_dict = {}

        document = aliased(Document, name='D')
        predication_aliases = []
        for idx, _ in enumerate(graph_query):
            predication_aliases.append(aliased(Predication, name='P{}'.format(idx)))

        projection_list = [document.id, document.title]
        for p in predication_aliases:
            projection_list.extend([p.subject_id, p.subject_str, p.subject_type, p.predicate_canonicalized, p.object_id,
                                    p.object_str, p.object_type, p.confidence, p.predicate, p.sentence])

        query = session.query(*projection_list).distinct()
        query = query.filter(document.collection == doc_collection)
        for pred in predication_aliases:
            query = query.filter(document.id == pred.document_id)

        for idx, (s, p, o) in enumerate(graph_query):
            pred = predication_aliases[idx]
            query = query.filter(pred.document_collection == doc_collection)

            # variable in pattern
            if s.startswith('?') or p.startswith('?') or o.startswith('?'):
                # the idea of the following blocks is as follows:
                # if x ( here subject, predicate or object) is not a var -> just add a where condition
                # if x is a variable
                # check if x already occurred -> yes join both aliased predication together
                # if x is new, just add it as the last predication of the variable
                if not s.startswith('?'):
                    query = query.filter(pred.subject_id == s)
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
                    query = query.filter(pred.object_id == o)
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

                if not p.startswith('?'):
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
                query = query.filter(pred.subject_id == s, pred.object_id == o, pred.predicate_canonicalized == p)

        # order by document id descending and limit results to 100
        query = query.order_by(document.id.desc()).limit(QUERY_LIMIT)

        return query, var_names

    def query_with_graph_query(self, graph_query, keyword_query='', doc_collection='PMC'):
        if len(graph_query) == 0:
            raise ValueError('graph query must contain at least one fact')

        session = Session.get()
        query, var_info = self.__construct_query(session, graph_query, doc_collection)

        sql_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=postgresql.dialect()))
        logging.info('executing sql statement: {}'.format(sql_query))
        var_names = []
        for v, _, _ in var_info:
            var_names.append(v)
        results = QueryResultAggregate(var_names)
        start = datetime.now()
        for r in session.execute(query):
            # extract var substitutions for pmid
            var2sub = {}
            for v, t, pred_pos in var_info:
                offset = 2 + pred_pos * 10

                if t == 'subject':
                    # it's ent_str, ent_id, ent_type
                    var2sub[v] = SUBSTITUTION(r[offset+1], r[offset], r[offset+2])
                elif t == 'object':
                    # it's ent_str, ent_id, ent_type
                    var2sub[v] = SUBSTITUTION(r[offset+5], r[offset+4], r[offset+6])
                elif t == 'predicate':
                    var2sub[v] = SUBSTITUTION(r[offset+3], 'predicate', 'predicate')
                else:
                    raise ValueError('Unknown position in query projection')

            # extract confidence & explanation for facts
            explanations = []
            conf = 0
            for i in range(0, len(graph_query)):
                offset = 2 + i * 10
                predicate_canonicalized = r[offset + 3]
                predicate = r[offset + 8]
                sentence = r[offset + 9]
                explanations.append(QueryFactExplanation(sentence, predicate, predicate_canonicalized))
                conf += float(r[offset+7])
            # create query result
            results.add_query_result(QueryResult(r[0], r[1], var2sub, conf, explanations))

        time_needed = datetime.now() - start
        self.query_logger.write_log(time_needed, 'openie', keyword_query, graph_query,
                                    sql_query.replace('\n', ' '), results.doc_ids)
        logging.info("{} hits: {}".format(results.result_size, results.doc_ids))
        return results

    @staticmethod
    def query_predicates_cleaned():
        session = Session.get()
        query = session.query(Predication.predicate_cleaned.distinct()).filter(Predication.predicate_cleaned.isnot(None))
        predicates = []
        start_time = datetime.now()
        for r in session.execute(query):
            predicates.append(r[0])

        logging.info('{} predicates queried in {}s'.format(len(predicates), datetime.now() - start_time))
        return predicates

    @staticmethod
    def query_entities():
        session = Session.get()
        query_subjects = session.query(Predication.subject_id, Predication.subject_str).distinct()
        query_objects = session.query(Predication.object_id, Predication.object_str).distinct()
        query = query_subjects.union(query_objects).distinct()

        entities = []
        start_time = datetime.now()
        for r in session.execute(query):
            ent_id, ent_str = r[0], r[1]
            entities.append((ent_id, ent_str))

        logging.info('{} entities queried in {}s'.format(len(entities), datetime.now() - start_time))
        return entities

