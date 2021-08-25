from unittest import TestCase

from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import ENTITY_TYPE_VARIABLE, MESH_ONTOLOGY
from narrant.entity.entity import Entity
from narrant.preprocessing.enttypes import DISEASE, DRUG, GENE


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

    def test_empty_query(self):
        fp = FactPattern([Entity('mtor', GENE)], "inhibits", [Entity("mtor", GENE)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual(None, optimized_q)

        fp = FactPattern([Entity('Simvastatin', DRUG)], "treats", [Entity("Disease", DISEASE)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertNotEqual(None, optimized_q)

    def test_mesh_ontology_queries(self):
        fp = FactPattern([Entity('D01.01231', MESH_ONTOLOGY)], "treats", [Entity("C012.21312", MESH_ONTOLOGY)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertNotEqual(None, optimized_q)

        fp = FactPattern([Entity('C01.01231', MESH_ONTOLOGY)], "treats", [Entity("C012.21312", MESH_ONTOLOGY)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual(None, optimized_q)

        fp = FactPattern([Entity('D01.01231', MESH_ONTOLOGY)], "administered", [Entity("E012.21312", MESH_ONTOLOGY)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertNotEqual(None, optimized_q)

    def test_partial_wrong_entities(self):
        fp = FactPattern([Entity('Simvastatin', DRUG)], "treats", [Entity("Hyper", DISEASE), Entity("Hyper", GENE)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual(1, len(optimized_q.fact_patterns[0].subjects))
        self.assertEqual("Simvastatin", optimized_q.fact_patterns[0].subjects[0].entity_id)
        self.assertEqual(1, len(optimized_q.fact_patterns[0].subjects))
        self.assertEqual("Hyper", optimized_q.fact_patterns[0].objects[0].entity_id)

        fp = FactPattern([Entity("Hyper", DISEASE), Entity("Hyper", GENE)], "treats", [Entity('Simvastatin', DRUG)])
        q = GraphQuery()
        q.add_fact_pattern(fp)
        optimized_q = QueryOptimizer.optimize_query(q)
        self.assertEqual(1, len(optimized_q.fact_patterns[0].subjects))
        self.assertEqual("Simvastatin", optimized_q.fact_patterns[0].subjects[0].entity_id)
        self.assertEqual(1, len(optimized_q.fact_patterns[0].subjects))
        self.assertEqual("Hyper", optimized_q.fact_patterns[0].objects[0].entity_id)

    def test_optimize_fact_pattern_correct_order(self):
        fp = FactPattern([Entity('A', DRUG)], "induces", [Entity("B", GENE)])
        optimized_fp = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
        self.assertEqual("A", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("B", next(iter(optimized_fp.objects)).entity_id)

        fp = FactPattern([Entity('B', DRUG)], "induces", [Entity("A", GENE)])
        optimized_fp = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
        self.assertIsNone(optimized_fp)

        fp = FactPattern([Entity('A', DRUG)], "decreases", [Entity("B", GENE)])
        optimized_fp = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
        self.assertEqual("A", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("B", next(iter(optimized_fp.objects)).entity_id)

        fp = FactPattern([Entity('B', DRUG)], "decreases", [Entity("A", GENE)])
        optimized_fp = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
        self.assertIsNone(optimized_fp)

        # should not flip this
        fp = FactPattern([Entity('B', DRUG)], "associated", [Entity("A", GENE)])
        optimized_fp = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
        self.assertEqual("B", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("A", next(iter(optimized_fp.objects)).entity_id)

        fp = FactPattern([Entity('A', DRUG)], "associated", [Entity("B", GENE)])
        optimized_fp = QueryOptimizer.optimize_symmetric_predicate_fp(fp)
        self.assertEqual("A", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("B", next(iter(optimized_fp.objects)).entity_id)

    def test_optimize_query_correct_order(self):
        q = GraphQuery([FactPattern([Entity('A', DRUG)], "induces", [Entity("B", GENE)])])
        optimized_q = QueryOptimizer.optimize_symmetric_predicate(q)
        self.assertEqual("A", next(iter(optimized_q.fact_patterns[0].subjects)).entity_id)
        self.assertEqual("B", next(iter(optimized_q.fact_patterns[0].objects)).entity_id)

        q = GraphQuery([FactPattern([Entity('B', DRUG)], "induces", [Entity("A", GENE)])])
        optimized_q = QueryOptimizer.optimize_symmetric_predicate(q)
        self.assertIsNone(optimized_q)

    def test_optimize_query_bug_variable(self):
        q = GraphQuery([FactPattern([Entity('?drug(Drug)', ENTITY_TYPE_VARIABLE)], "interacts",
                                    [Entity('cyp3a4', GENE), Entity('D08.811.682.690.708.170.495.500',
                                                                    MESH_ONTOLOGY)])])
        optimized_q = QueryOptimizer.optimize_query(q)
        optimized_fp = optimized_q.fact_patterns[0]
        self.assertEqual("?drug(Drug)", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("cyp3a4", next(iter(optimized_fp.objects)).entity_id)

    def test_optimize_query_bug_variable_OR(self):
        q = GraphQuery(
            [FactPattern([Entity('?drug(Drug)', ENTITY_TYPE_VARIABLE)], "interacts", [Entity('cyp3a4', GENE)]),
             FactPattern([Entity('?drug(Drug)', ENTITY_TYPE_VARIABLE)], "interacts",
                         [Entity('D08.811.682.690.708.170.495.500', MESH_ONTOLOGY)])])
        optimized_q = QueryOptimizer.optimize_query(q, and_mod=False)
        optimized_fp = optimized_q.fact_patterns[0]
        self.assertEqual("?drug(Drug)", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("cyp3a4", next(iter(optimized_fp.objects)).entity_id)

        optimized_fp = optimized_q.fact_patterns[1]
        self.assertEqual("?drug(Drug)", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("D08.811.682.690.708.170.495.500", next(iter(optimized_fp.objects)).entity_id)

    def test_optimize_query_bug_variable_AND(self):
        q = GraphQuery(
            [FactPattern([Entity('?drug(Drug)', ENTITY_TYPE_VARIABLE)], "interacts", [Entity('cyp3a4', GENE)]),
             FactPattern([Entity('?drug(Drug)', ENTITY_TYPE_VARIABLE)], "interacts",
                         [Entity('D08.811.682.690.708.170.495.500', MESH_ONTOLOGY)])])
        optimized_q = QueryOptimizer.optimize_query(q, and_mod=True)
        optimized_fp = optimized_q.fact_patterns[0]
        self.assertEqual("?drug(Drug)", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("cyp3a4", next(iter(optimized_fp.objects)).entity_id)

        optimized_fp = optimized_q.fact_patterns[1]
        self.assertEqual("?drug(Drug)", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("D08.811.682.690.708.170.495.500", next(iter(optimized_fp.objects)).entity_id)

    def test_optimize_query_NOT_AND(self):
        q = GraphQuery([FactPattern([Entity('?drug(Drug)', DRUG)], "metabolises", [Entity('drug2', DRUG)]),
                        FactPattern([Entity('?drug(Drug)', DRUG)], "metabolises",
                                    [Entity('D08.811.682.690.708.170.495.500', DRUG)])])
        optimized_q = QueryOptimizer.optimize_query(q, and_mod=True)
        self.assertIsNone(optimized_q)

    def test_optimize_query_NOT_NONE_OR(self):
        q = GraphQuery([FactPattern([Entity('?drug(Drug)', DRUG)], "metabolises", [Entity('cyp3a4', GENE)]),
                        FactPattern([Entity('?drug(Drug)', DRUG)], "metabolises",
                                    [Entity('D08.811.682.690.708.170.495.500', DRUG)])])
        optimized_q = QueryOptimizer.optimize_query(q, and_mod=False)
        self.assertEqual(1, len(optimized_q.fact_patterns))
        optimized_fp = optimized_q.fact_patterns[0]
        self.assertEqual("cyp3a4", next(iter(optimized_fp.subjects)).entity_id)
        self.assertEqual("?drug(Drug)", next(iter(optimized_fp.objects)).entity_id)
