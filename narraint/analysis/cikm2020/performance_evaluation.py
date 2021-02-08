import logging
import random
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import aliased

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.entity.entity import Entity
from narraint.entity.enttypes import GENE, SPECIES
from narraint.extraction.versions import PATHIE_EXTRACTION
from narraint.progress import print_progress_with_eta
from narraint.queryengine.engine import VAR_NAME, VAR_TYPE, VAR_TYPE_PREDICATE, QueryEngine
from narraint.queryengine.query import GraphQuery, FactPattern

RANDOM_FACTS = 100000
QUERIES_WITH_ONE_PRED = 1000
QUERIES_WITH_TWO_PRED = 1000
QUERIES_WITH_THREE_PRED = 1000
QUERIES_WITH_VAR_1 = 100
QUERIES_WITH_VAR_2 = 100


class PerformanceQueryEngine:
    """
    This class is a small version of the QueryEngine
    It supports the translation into a SQL statement and measures the performance for translation and execution
    The times are measured by COUNT(*) queries
    """

    def __init__(self):
        self.query_engine = QueryEngine()

    def __construct_query(self, session, graph_query, doc_collection, extraction_type):
        var_names = []
        var_dict = {}

        predication_aliases = []
        for idx, _ in enumerate(graph_query):
            predication_aliases.append(aliased(Predication, name='P{}'.format(idx)))

        p0 = predication_aliases[0]
        query = session.query(func.count())
        for pred in predication_aliases:
            query = query.filter(p0.document_id == pred.document_id)

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
                    query = query.filter(pred.subject_id == s)
                    if s_t in [GENE, SPECIES]:
                        query = query.filter(pred.subject_type == s_t)
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
                    if o_t in [GENE, SPECIES]:
                        query = query.filter(pred.object_type == o_t)
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
                if s_t in [GENE, SPECIES]:
                    query = query.filter(pred.subject_type == s_t)
                if o_t in [GENE, SPECIES]:
                    query = query.filter(pred.object_type == o_t)

        return query, var_names

    def query_with_graph_query(self, facts, doc_collection):
        if len(facts) == 0:
            raise ValueError('graph query must contain at least one fact')

        graph_query = GraphQuery()
        for f in facts:
            graph_query.add_fact_pattern(FactPattern([Entity(f[0], f[1])],
                                                     f[2], [Entity(f[3], f[4])]))

        time_before_query = datetime.now()
        results, limit_hit = self.query_engine.process_query_with_expansion(graph_query, doc_collection)
        time_after_query = datetime.now()
        result_size = len(set([r.document_id for r in results]))

        #    session = Session.get()
        #   time_before_translation = datetime.now()
        #  query, var_info = self.__construct_query(session, graph_query, doc_collection, extraction_type)
        # time_after_translation = datetime.now()
        # time_before_query = datetime.now()
        # result_size = 0
        # for r in session.execute(query):
        #    result_size = r[0]
        # time_after_query = datetime.now()

        return (time_after_query - time_before_query), result_size


def main():
    """
    Performes the performance evaluation and stores the results as .tsv files
    """
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    session = Session.get()
    q = session.query(Predication.subject_id, Predication.subject_type, Predication.predicate_canonicalized,
                      Predication.object_id, Predication.object_type) \
        .filter(Predication.predicate_canonicalized != None) \
        .filter(Predication.extraction_type == PATHIE_EXTRACTION) \
        .filter(Predication.document_collection == 'PubMed') \
        .order_by(func.random()).limit(RANDOM_FACTS)

    logging.info('Querying {} randomly sampled facts'.format(RANDOM_FACTS))
    facts = set()
    for r in session.execute(q):
        fact = (r[0], r[1], r[2], r[3], r[4])
        facts.add(fact)
    logging.info('{} unique facts retrieved'.format(len(facts)))
    with open('performance_selected_facts.tsv', 'wt') as f:
        f.write('subject\tsubject_type\tpredicate_canonicalized\tobject\tobject_type')
        for s, s_t, p, o, o_t in facts:
            f.write('\n{}\t{}\t{}\t{}\t'.format(s, s_t, p, o, o_t))

    logging.info('init query engine...')
    engine = PerformanceQueryEngine()

    logging.info('I: analysing performance: queries with 1 predicate...')
    with open('performance_query_1.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_ONE_PRED):
            fact_query = random.sample(facts, k=1)
            time_query, result_size = engine.query_with_graph_query(fact_query, "PubMed")
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance I', i, QUERIES_WITH_ONE_PRED, start_time, print_every_k=1)

    logging.info('II: analysing performance: queries with 2 predicates...')
    with open('performance_query_2.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_TWO_PRED):
            fact_query = random.sample(facts, k=2)
            time_query, result_size = engine.query_with_graph_query(fact_query, "PubMed")
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance II', i, QUERIES_WITH_TWO_PRED, start_time, print_every_k=1)

    logging.info('III: analysing performance: queries with 3 predicate...')
    with open('performance_query_3.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_THREE_PRED):
            fact_query = random.sample(facts, k=3)
            time_query, result_size = engine.query_with_graph_query(fact_query, "PubMed")
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance III', i, QUERIES_WITH_THREE_PRED, start_time, print_every_k=1)

    logging.info('IV: analysing performance: queries with 1 variable and 1 predicate...')
    with open('performance_query_variable_1.tsv', 'wt') as fp:
        fp.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_VAR_1):
            fact_query = random.sample(facts, k=1)
            if random.random() < 0.5:
                f = fact_query[0]
                fact_query[0] = ('?X', 'Variable', f[2], f[3], f[4])
            else:
                f = fact_query[0]
                fact_query[0] = (f[0], f[1], f[2], '?X', 'Variable')
            time_query, result_size = engine.query_with_graph_query(fact_query, "PubMed")
            fp.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance variable I', i, QUERIES_WITH_VAR_1, start_time,
                                    print_every_k=1)

    logging.info('V: analysing performance: queries with 1 variable and 2 predicate...')
    with open('performance_query_variable_2.tsv', 'wt') as fp:
        fp.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_VAR_2):
            fact_query = random.sample(facts, k=2)
            if random.random() < 0.5:
                f = fact_query[0]
                fact_query[0] = ('?X', 'Variable', f[2], f[3], f[4])
                f2 = fact_query[1]
                fact_query[1] = (f2[0], f2[1], f2[2], '?X', 'Variable')
            else:
                f = fact_query[0]
                fact_query[0] = (f[0], f[1], f[2], '?X', 'Variable')
                f2 = fact_query[1]
                fact_query[1] = ('?X', 'Variable', f2[2], f2[3], f2[4])

            time_query, result_size = engine.query_with_graph_query(fact_query, "PubMed")
            fp.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance variable II', i, QUERIES_WITH_VAR_2, start_time,
                                    print_every_k=1)


if __name__ == "__main__":
    main()
