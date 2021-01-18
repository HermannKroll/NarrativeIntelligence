from unittest import TestCase

from narraint.entity.entity import Entity
from narraint.entity.enttypes import DISEASE, DRUG, GENE
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query_hints import ENTITY_TYPE_VARIABLE


class QueryOptimizerTestCase(TestCase):

    def test_optimize_predicate_types_for_fact_pattern(self):
        """
        Tests whether the QueryOptimizer does change the order of subject and object correctly based on type constraints
        :return:
        """
        fact_pattern = FactPattern([Entity("Diabetes", DISEASE)], "treats", [Entity('Metformin', DRUG)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("Metformin", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Diabetes", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity('Metformin', DRUG)], "treats", [Entity("Diabetes", DISEASE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("Metformin", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Diabetes", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity('Metformin', DRUG)], "decreases", [Entity("Diabetes", DISEASE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("Metformin", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Diabetes", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity("Diabetes", DISEASE)], "decreases", [Entity('Metformin', DRUG)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("Diabetes", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Metformin", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity('Metformin', DRUG)], "inhibits", [Entity("mtor", GENE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("Metformin", optimized_fp.subjects[0].entity_id)
        self.assertEqual("mtor", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity('mtor', GENE)], "inhibits", [Entity("Metformin", DRUG)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("Metformin", optimized_fp.subjects[0].entity_id)
        self.assertEqual("mtor", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity('Simvastatin', DRUG)], "metabolises", [Entity("cyp3a4", GENE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("cyp3a4", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Simvastatin", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity('cyp3a4', GENE)], "metabolises", [Entity("Simvastatin", DRUG)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("cyp3a4", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Simvastatin", optimized_fp.objects[0].entity_id)

    def test_optimize_predicate_types_for_fact_pattern_variables(self):
        """
        Tests whether the QueryOptimizer does change the order of subject and object correctly based on type constraints
        This time variables are tested
        :return:
        """
        fact_pattern = FactPattern([Entity("?X(Drug)", ENTITY_TYPE_VARIABLE)], "treats", [Entity('Diabetes', DISEASE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("?X(Drug)", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Diabetes", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity("Diabetes", DISEASE)], "treats", [Entity('?X(Drug)', ENTITY_TYPE_VARIABLE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("?X(Drug)", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Diabetes", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity("Diabetes", DISEASE)], "treats", [Entity('?X', ENTITY_TYPE_VARIABLE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("?X", optimized_fp.subjects[0].entity_id)
        self.assertEqual("Diabetes", optimized_fp.objects[0].entity_id)

        fact_pattern = FactPattern([Entity("?X", ENTITY_TYPE_VARIABLE)], "treats", [Entity('?Y', ENTITY_TYPE_VARIABLE)])
        optimized_fp = QueryOptimizer.optimize_predicate_types_for_fact_pattern(fact_pattern)
        self.assertEqual("?X", optimized_fp.subjects[0].entity_id)
        self.assertEqual("?Y", optimized_fp.objects[0].entity_id)

    def test_optimize_graph_query(self):
        """
        Tests if the graph query is optimized correctly
        :return:
        """
        fp = FactPattern([Entity('mtor', GENE), Entity('mtor', GENE)], "inhibits",
                         [Entity("Metformin", DRUG), Entity("Metformin", DRUG)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual(1, len(optimized_q.fact_patterns[0].subjects))
        self.assertEqual(1, len(optimized_q.fact_patterns[0].objects))
        self.assertEqual("Metformin", optimized_q.fact_patterns[0].subjects[0].entity_id)
        self.assertEqual("inhibits", optimized_q.fact_patterns[0].predicate)
        self.assertEqual("mtor", optimized_q.fact_patterns[0].objects[0].entity_id)

        fp1 = FactPattern([Entity("?X(Drug)", ENTITY_TYPE_VARIABLE)], "treats", [Entity('Diabetes', DISEASE)])
        fp2 = FactPattern([Entity('mtor', GENE)], "inhibits", [Entity("Metformin", DRUG)])
        q = GraphQuery()
        q.add_fact_pattern(fp1)
        q.add_fact_pattern(fp2)

        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual("Metformin", optimized_q.fact_patterns[0].subjects[0].entity_id)
        self.assertEqual("inhibits", optimized_q.fact_patterns[0].predicate)
        self.assertEqual("mtor", optimized_q.fact_patterns[0].objects[0].entity_id)

        self.assertEqual("?X(Drug)", optimized_q.fact_patterns[1].subjects[0].entity_id)
        self.assertEqual("treats", optimized_q.fact_patterns[1].predicate)
        self.assertEqual("Diabetes", optimized_q.fact_patterns[1].objects[0].entity_id)

        q = GraphQuery()
        q.add_fact_pattern(fp1)
        q.add_fact_pattern(fp1)
        q.add_fact_pattern(fp2)
        q.add_fact_pattern(fp2)

        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual(2, len(optimized_q.fact_patterns))
        self.assertEqual("Metformin", optimized_q.fact_patterns[0].subjects[0].entity_id)
        self.assertEqual("inhibits", optimized_q.fact_patterns[0].predicate)
        self.assertEqual("mtor", optimized_q.fact_patterns[0].objects[0].entity_id)

        self.assertEqual("?X(Drug)", optimized_q.fact_patterns[1].subjects[0].entity_id)
        self.assertEqual("treats", optimized_q.fact_patterns[1].predicate)
        self.assertEqual("Diabetes", optimized_q.fact_patterns[1].objects[0].entity_id)