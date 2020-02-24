import logging
import re
from datetime import datetime

from sqlalchemy.orm import aliased

from narraint.backend.models import Document, Predication
from narraint.backend.database import Session
from sqlalchemy.dialects import postgresql

from narraint.openie.querylogger import QueryLogger

QUERY_LIMIT = 100
VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE = re.compile(r'\((\w+)\)')
VAR_TYPE_PREDICATE = re.compile(r'\((\w+),(\w+)\)')

query_logger = QueryLogger()


def __construct_query(session, graph_query, doc_collection):
    var_names = []
    var_dict = {}

    document = aliased(Document, name='D')
    predication_aliases = []
    for idx, _ in enumerate(graph_query):
        predication_aliases.append(aliased(Predication, name='P{}'.format(idx)))

    projection_list = [document.id, document.title]
    for p in predication_aliases:
        projection_list.extend([p.subject_id, p.subject_str, p.subject_type, p.predicate_cleaned, p.object_id,
                                p.object_str, p.object_type, p.confidence])

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
                search_term = "%{}%".format(p)
                query = query.filter(pred.predicate_cleaned.like(search_term))
            else:
                query = query.filter(pred.predicate_cleaned.isnot(None))
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
                        query = query.filter(pred.predicate_cleaned == last_pred.predicate_cleaned)
                    else:
                        raise ValueError('Variable cannot be used as predicate and subject / object.')
        else:
            search_term = "%{}%".format(p)
            query = query.filter(pred.subject_id == s, pred.object_id == o, pred.predicate_cleaned.like(search_term))

    # order by document id descending and limit results to 100
    query = query.order_by(document.id.desc()).limit(QUERY_LIMIT)

    return query, var_names


def query_with_graph_query(graph_query, keyword_query='', doc_collection='PMC'):
    if len(graph_query) == 0:
        raise ValueError('graph query must contain at least one fact')

    session = Session.get()
    query, var_info = __construct_query(session, graph_query, doc_collection)

    sql_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}, dialect=postgresql.dialect()))
    logging.info('executing sql statement: {}'.format(sql_query))
    pmids, titles, var_subs, var_names = [], [], [], []
    start = datetime.now()
    for v, _, _ in var_info:
        var_names.append(v)
    for r in session.execute(query):
        pmids.append(r[0])
        titles.append(r[1])
        # extract var substitutions for pmid
        var_sub = {}
        for v, t, pred_pos in var_info:
            offset = 2 + pred_pos * 8
            if t == 'subject':
                var_sub[v] = '{} ({} : {})'.format(r[offset+1], r[offset], r[offset+2])
            elif t == 'object':
                var_sub[v] = '{} ({} : {})'.format(r[offset+5], r[offset+4], r[offset+6])
            elif t == 'predicate':
                var_sub[v] = '{}'.format(r[offset+3])
            else:
                raise ValueError('Unknown position in query projection')

        conf = 0
        for i in range(0, len(graph_query)):
            conf += float(r[2+7+i*8])
        var_sub["conf"] = '{:4.2f} / {}'.format(conf, len(graph_query))
        var_subs.append(var_sub)
    #var_names.append("conf")
    time_needed = datetime.now() - start
    query_logger.write_log(time_needed, 'openie', keyword_query, graph_query, sql_query.replace('\n', ' '), pmids)

    logging.info("{} hits: {}".format(len(pmids), pmids))
    return pmids, titles, var_subs, var_names



