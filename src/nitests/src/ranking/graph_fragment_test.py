from unittest import TestCase

from kgextractiontoolbox.document.document import TaggedEntity
from kgextractiontoolbox.document.narrative_document import NarrativeDocument, StatementExtraction
from narraint.queryengine.query import FactPattern
from narraint.queryengine.query_hints import DO_NOT_CARE_PREDICATE
from narraint.ranking.graph_fragment import GraphFragmentExtractor
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narrant.entity.entity import Entity


class GraphFragmentTest(TestCase):

    def setUp(self):
        tags = [TaggedEntity(document=1, ent_id="A1", ent_type="AT", start=1, end=2),
                TaggedEntity(document=1, ent_id="A2", ent_type="AT", start=1, end=2),
                TaggedEntity(document=1, ent_id="B", ent_type="BT", start=1, end=2),
                TaggedEntity(document=1, ent_id="C", ent_type="CT", start=1, end=2),
                TaggedEntity(document=1, ent_id="D", ent_type="DT", start=1, end=2)]

        stmts = [StatementExtraction(subject_id="A1", subject_type="AT", subject_str="",
                                     predicate="", relation="r1",
                                     object_id="B", object_type="BT", object_str="",
                                     sentence_id=1, confidence=1.0),
                 StatementExtraction(subject_id="A2", subject_type="AT", subject_str="",
                                     predicate="", relation="r1",
                                     object_id="B", object_type="BT", object_str="",
                                     sentence_id=1, confidence=1.0),
                 StatementExtraction(subject_id="A1", subject_type="AT", subject_str="",
                                     predicate="", relation="r3",
                                     object_id="C", object_type="CT", object_str="",
                                     sentence_id=1, confidence=1.0),
                 StatementExtraction(subject_id="C", subject_type="CT", subject_str="",
                                     predicate="", relation="r4",
                                     object_id="D", object_type="DT", object_str="",
                                     sentence_id=1, confidence=1.0)
                 ]

        # two connections between A and B and one connection between A and C
        # 1. A1 - r1 - B AND A - r3 - C AND C - r4 - D
        # 2. A2 - r1 - B and A - r3 - C AND C - r4 - D

        self.index_document = IndexedDocument(NarrativeDocument(document_id=1,
                                                                title="Test",
                                                                abstract="This is a test abstract",
                                                                metadata=None,
                                                                tags=tags,
                                                                extracted_statements=stmts), "PubMed")

        self.stmts = self.index_document.scored_statements

    def test_graph_fragment_one_match(self):
        # the first query has one match
        query = AnalyzedQuery(fact_patterns=[FactPattern(subjects=[Entity("A1", "AT")],
                                                         predicate="r1",
                                                         objects=[Entity("B", "BT")]),
                                             FactPattern(subjects=[Entity("A1", "AT")],
                                                         predicate="r3",
                                                         objects=[Entity("C", "CT")])
                                             ])

        fragments = GraphFragmentExtractor.matches(query, self.index_document)
        self.assertEqual(1, len(fragments))
        fragment = fragments[0]
        # statement 1 and 3 match the query, i.e. the fragment must match both
        self.assertIn(fragment[0], self.stmts)
        self.assertIn(fragment[1], self.stmts)

    def test_graph_fragment_two_matches(self):
        # the second query has one match
        query = AnalyzedQuery(fact_patterns=[FactPattern(subjects=[Entity("A1", "AT"),
                                                                   Entity("A2", "AT")],
                                                         predicate="r1",
                                                         objects=[Entity("B", "BT")]),
                                             FactPattern(subjects=[Entity("A1", "AT")],
                                                         predicate="r3",
                                                         objects=[Entity("C", "CT")])
                                             ])

        fragments = GraphFragmentExtractor.matches(query, self.index_document)
        self.assertEqual(2, len(fragments))
        # each fragment must contain two statements
        self.assertEqual(2, len(fragments[0]))
        self.assertEqual(2, len(fragments[0]))  #

        fragment = fragments[0]
        # statement 1 and 3 match the query, i.e. the fragment must match both
        self.assertIn(fragment[0], self.stmts)
        self.assertIn(fragment[1], self.stmts)

        fragment = fragments[1]
        # statement 1 and 3 match the query, i.e. the fragment must match both
        self.assertIn(fragment[0], self.stmts)
        self.assertIn(fragment[1], self.stmts)

    def test_graph_fragment_two_matches_three_fp(self):
        # the second query has one match
        query = AnalyzedQuery(fact_patterns=[FactPattern(subjects=[Entity("A1", "AT"),
                                                                   Entity("A2", "AT")],
                                                         predicate="r1",
                                                         objects=[Entity("B", "BT")]),
                                             FactPattern(subjects=[Entity("A1", "AT")],
                                                         predicate="r3",
                                                         objects=[Entity("C", "CT")]),
                                             FactPattern(subjects=[Entity("C", "CT")],
                                                         predicate="r4",
                                                         objects=[Entity("D", "DT")])
                                             ])

        fragments = GraphFragmentExtractor.matches(query, self.index_document)
        self.assertEqual(2, len(fragments))
        # each fragment must contain three statements
        self.assertEqual(3, len(fragments[0]))
        self.assertEqual(3, len(fragments[0]))
        fragment = fragments[0]
        # statement 1 and 3 match the query, i.e. the fragment must match both
        self.assertIn(fragment[0], self.stmts)
        self.assertIn(fragment[1], self.stmts)
        self.assertIn(fragment[2], self.stmts)

        fragment = fragments[1]
        # statement 1 and 3 match the query, i.e. the fragment must match both
        self.assertIn(fragment[0], self.stmts)
        self.assertIn(fragment[1], self.stmts)
        self.assertIn(fragment[2], self.stmts)

    def test_graph_fragment_no_match(self):
        # the second query has one match
        query = AnalyzedQuery(fact_patterns=[FactPattern(subjects=[Entity("X", "AT"),
                                                                   Entity("A2", "AT")],
                                                         predicate="r1",
                                                         objects=[Entity("Y", "BT")])
                                             ])

        fragments = GraphFragmentExtractor.matches(query, self.index_document)
        self.assertEqual(0, len(fragments))

    def test_graph_fragment_do_not_care(self):
        # the first query has one match
        query = AnalyzedQuery(fact_patterns=[FactPattern(subjects=[Entity("A1", "AT"),
                                                                   Entity("A2", "AT")],
                                                         predicate=DO_NOT_CARE_PREDICATE,
                                                         objects=[Entity("B", "BT")]),
                                             FactPattern(subjects=[Entity("A1", "AT")],
                                                         predicate="r3",
                                                         objects=[Entity("C", "CT")])
                                             ])

        fragments = GraphFragmentExtractor.matches(query, self.index_document)
        self.assertEqual(2, len(fragments))
        for fragment in fragments:
            # statement 1 and 3 match the query, i.e. the fragment must match both
            self.assertIn(fragment[0], self.stmts)
            self.assertIn(fragment[1], self.stmts)
