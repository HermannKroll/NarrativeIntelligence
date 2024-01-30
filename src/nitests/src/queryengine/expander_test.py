from unittest import TestCase

from narraint.queryengine.expander import QueryExpander
from narraint.queryengine.query import FactPattern, GraphQuery
from narrant.entity.entity import Entity
from narrant.entitylinking.enttypes import DISEASE, DRUG, GENE, CHEMICAL


class QueryExpanderTestCase(TestCase):

    def test_expand_associated(self):
        fp = FactPattern([Entity('Simvastatin', DRUG)], 'associated', [Entity('Hyper', DISEASE)])
        fp2 = FactPattern([Entity('Metformin', DRUG)], 'associated', [Entity('mtor', GENE)])
        queries_expanded = QueryExpander.expand_query(GraphQuery([fp, fp2]))

        self.assertEqual(2, len(queries_expanded))
        self.assertEqual("Simvastatin", next(iter(queries_expanded[0].fact_patterns[0].subjects)).entity_id)
        self.assertEqual("Hyper", next(iter(queries_expanded[0].fact_patterns[0].objects)).entity_id)
        self.assertEqual("Hyper", next(iter(queries_expanded[0].fact_patterns[1].subjects)).entity_id)
        self.assertEqual("Simvastatin", next(iter(queries_expanded[0].fact_patterns[1].objects)).entity_id)

        self.assertEqual("Metformin", next(iter(queries_expanded[1].fact_patterns[0].subjects)).entity_id)
        self.assertEqual("mtor", next(iter(queries_expanded[1].fact_patterns[0].objects)).entity_id)
        self.assertEqual("mtor", next(iter(queries_expanded[1].fact_patterns[1].subjects)).entity_id)
        self.assertEqual("Metformin", next(iter(queries_expanded[1].fact_patterns[1].objects)).entity_id)

    def test_expand_interacts(self):
        fp = FactPattern([Entity('Metformin', DRUG)], 'interacts', [Entity('mtor', GENE)])
        queries_expanded = QueryExpander.expand_query(GraphQuery([fp]))

        self.assertEqual(1, len(queries_expanded))
        self.assertEqual(6, len(queries_expanded[0].fact_patterns))
        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[0].subjects)).entity_id)
        self.assertEqual("interacts", queries_expanded[0].fact_patterns[0].predicate)
        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[0].objects)).entity_id)

        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[1].subjects)).entity_id)
        self.assertEqual("metabolises", queries_expanded[0].fact_patterns[1].predicate)
        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[1].objects)).entity_id)

        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[2].subjects)).entity_id)
        self.assertEqual("inhibits", queries_expanded[0].fact_patterns[2].predicate)
        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[2].objects)).entity_id)

        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[3].subjects)).entity_id)
        self.assertEqual("interacts", queries_expanded[0].fact_patterns[3].predicate)
        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[3].objects)).entity_id)

        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[4].subjects)).entity_id)
        self.assertEqual("metabolises", queries_expanded[0].fact_patterns[4].predicate)
        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[4].objects)).entity_id)

        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[5].subjects)).entity_id)
        self.assertEqual("inhibits", queries_expanded[0].fact_patterns[5].predicate)
        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[5].objects)).entity_id)

    def test_do_not_expand(self):
        fp = FactPattern([Entity('Metformin', CHEMICAL)], 'inhibits', [Entity('mtor', GENE)])
        queries_expanded = QueryExpander.expand_query(GraphQuery([fp]))

        self.assertEqual(1, len(queries_expanded))
        self.assertEqual(1, len(queries_expanded[0].fact_patterns))
        self.assertEqual("Metformin", next(iter(queries_expanded[0].fact_patterns[0].subjects)).entity_id)
        self.assertEqual("inhibits", queries_expanded[0].fact_patterns[0].predicate)
        self.assertEqual("mtor", next(iter(queries_expanded[0].fact_patterns[0].objects)).entity_id)
