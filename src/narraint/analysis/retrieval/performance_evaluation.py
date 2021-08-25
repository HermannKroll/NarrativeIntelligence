import logging
import random
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narraint.frontend.entity.query_translation import QueryTranslation
from narrant.entity.entity import Entity
from narraint.extraction.versions import PATHIE_EXTRACTION
from narrant.entity.entityresolver import EntityResolver
from narrant.progress import print_progress_with_eta
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.query import GraphQuery, FactPattern

RANDOM_FACTS = 1000000
QUERIES_WITH_ONE_PRED = 10000
QUERIES_WITH_TWO_PRED = 10000
QUERIES_WITH_THREE_PRED = 10000
QUERIES_WITH_VAR_1 = 0
QUERIES_WITH_VAR_2 = 0


class PerformanceQueryEngine:
    """
    This class is a small version of the QueryEngine
    It supports the translation into a SQL statement and measures the performance for translation and execution
    The times are measured by COUNT(*) queries
    """

    def __init__(self):
        self.translation = QueryTranslation()
        self.resolver = EntityResolver.instance()

    def compute_query_with_expansion(self, facts):
        graph_query = GraphQuery()
        for f in facts:
            if f[0].startswith('MESH'):
                try:
                    subjects = self.translation.entity_tagger.tag_entity(self.resolver.get_name_for_var_ent_id(f[0], f[1]))
                except:
                    subjects = [Entity(f[0], f[1])]
            else:
                subjects = [Entity(f[0], f[1])]
            if f[3].startswith('MESH'):
                try:
                    objects = self.translation.entity_tagger.tag_entity(self.resolver.get_name_for_var_ent_id(f[3], f[4]))
                except:
                    objects = [Entity(f[3], f[4])]
            else:
                objects = [Entity(f[3], f[4])]
            graph_query.add_fact_pattern(FactPattern(subjects, f[2], objects))
        return graph_query

    def compute_query(self, facts):
        graph_query = GraphQuery()
        for f in facts:
            graph_query.add_fact_pattern(FactPattern([Entity(f[0], f[1])], f[2], [Entity(f[3], f[4])]))
        return graph_query

    def query_with_graph_query(self, graph_query: GraphQuery):
        if len(graph_query.fact_patterns) == 0:
            raise ValueError('graph query must contain at least one fact')


        time_before_query = datetime.now()
        results, limit_hit = QueryEngine.process_query_with_expansion(graph_query)
        time_after_query = datetime.now()
        result_size = len(set([r.document_id for r in results]))

        #    session = SessionExtended.get()
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

    session = SessionExtended.get()
    q = session.query(Predication.document_id,
                      Predication.subject_id, Predication.subject_type,
                      Predication.relation,
                      Predication.object_id, Predication.object_type) \
        .filter(Predication.relation != None) \
        .filter(Predication.extraction_type == PATHIE_EXTRACTION) \
        .filter(Predication.document_collection == 'PubMed') \
        .order_by(func.random()).limit(RANDOM_FACTS)

    logging.info('Querying {} randomly sampled facts'.format(RANDOM_FACTS))
    facts = set()
    doc2facts = defaultdict(set)
    for r in session.execute(q):
        fact = (r[1], r[2], r[3], r[4], r[5])
        facts.add(fact)
        doc2facts[r[0]].add(fact)

    doc2facts_2 = set()
    doc2facts_3 = set()
    for _, facts_in_doc in doc2facts.items():
        if len(facts_in_doc) >= 2:
            doc2facts_2.add(frozenset(facts_in_doc))
        if len(facts_in_doc) >= 3:
            doc2facts_3.add(frozenset(facts_in_doc))

    logging.info('{} unique facts retrieved'.format(len(facts)))
    logging.info('{} unique 2-facts retrieved'.format(len(doc2facts_2)))
    logging.info('{} unique 3-facts retrieved'.format(len(doc2facts_3)))
    with open('performance_selected_facts.tsv', 'wt') as f:
        f.write('subject\tsubject_type\trelation\tobject\tobject_type')
        for s, s_t, p, o, o_t in facts:
            f.write('\n{}\t{}\t{}\t{}\t'.format(s, s_t, p, o, o_t))

    logging.info('init query engine...')
    engine = PerformanceQueryEngine()

    logging.info('I: analysing performance: queries with 1 predicate...')
    with open('performance_query_1.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_ONE_PRED):
            fact = random.sample(facts, k=1)
            fact_query = engine.compute_query(fact)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance I', i, QUERIES_WITH_ONE_PRED, start_time, print_every_k=1)

    logging.info('I: analysing performance: queries with 1 predicate...')
    with open('performance_query_1_with_exp.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_ONE_PRED):
            fact = random.sample(facts, k=1)
            fact_query = engine.compute_query_with_expansion(fact)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance I', i, QUERIES_WITH_ONE_PRED, start_time, print_every_k=1)

    logging.info('II: analysing performance: queries with 2 predicates...')
    with open('performance_query_2.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_TWO_PRED):
            facts = random.sample(random.sample(doc2facts_2, k=1)[0], k=2)
            fact_query = engine.compute_query(facts)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance II', i, QUERIES_WITH_TWO_PRED, start_time, print_every_k=1)

    logging.info('II: analysing performance: queries with 2 predicates...')
    with open('performance_query_2_with_exp.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_TWO_PRED):
            facts = random.sample(random.sample(doc2facts_2, k=1)[0], k=2)
            fact_query = engine.compute_query_with_expansion(facts)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance II', i, QUERIES_WITH_TWO_PRED, start_time, print_every_k=1)

    logging.info('III: analysing performance: queries with 3 predicate...')
    with open('performance_query_3.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_THREE_PRED):
            facts = random.sample(random.sample(doc2facts_2, k=1)[0], k=2)
            fact_query = engine.compute_query(facts)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance III', i, QUERIES_WITH_THREE_PRED, start_time, print_every_k=1)

    logging.info('III: analysing performance: queries with 3 predicate...')
    with open('performance_query_3_with_exp.tsv', 'wt') as f:
        f.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_THREE_PRED):
            facts = random.sample(random.sample(doc2facts_2, k=1)[0], k=2)
            fact_query = engine.compute_query_with_expansion(facts)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            f.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance III', i, QUERIES_WITH_THREE_PRED, start_time, print_every_k=1)


    logging.info('IV: analysing performance: queries with 1 variable and 1 predicate...')
    with open('performance_query_variable_1.tsv', 'wt') as fp:
        fp.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_VAR_1):
            facts = random.sample(facts, k=1)
            if random.random() < 0.5:
                f = facts[0]
                facts[0] = ('?X', 'Variable', f[2], f[3], f[4])
            else:
                f = facts[0]
                facts[0] = (f[0], f[1], f[2], '?X', 'Variable')
            fact_query = engine.compute_query(facts)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            fp.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance variable I', i, QUERIES_WITH_VAR_1, start_time,
                                    print_every_k=1)

    logging.info('V: analysing performance: queries with 1 variable and 2 predicate...')
    with open('performance_query_variable_2.tsv', 'wt') as fp:
        fp.write('time_query\tresult_size\tquery')
        start_time = datetime.now()
        for i in range(0, QUERIES_WITH_VAR_2):
            facts = random.sample(facts, k=2)
            if random.random() < 0.5:
                f = facts[0]
                facts[0] = ('?X', 'Variable', f[2], f[3], f[4])
                f2 = facts[1]
                facts[1] = (f2[0], f2[1], f2[2], '?X', 'Variable')
            else:
                f = facts[0]
                facts[0] = (f[0], f[1], f[2], '?X', 'Variable')
                f2 = facts[1]
                facts[1] = ('?X', 'Variable', f2[2], f2[3], f2[4])

            fact_query = engine.compute_query(facts)
            time_query, result_size = engine.query_with_graph_query(fact_query)
            fp.write('\n{}\t{}\t{}'.format(time_query, result_size, fact_query))
            print_progress_with_eta('analysing performance variable II', i, QUERIES_WITH_VAR_2, start_time,
                                    print_every_k=1)


if __name__ == "__main__":
    main()
