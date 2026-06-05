from unittest import TestCase
from kgextractiontoolbox.document.document import TaggedEntity
from kgextractiontoolbox.document.narrative_document import NarrativeDocument, StatementExtraction
from narrant.entity.entity import get_unique_entity_key
from narraint.ranking.indexed_document import IndexedDocument, ScoredDocumentEntity, ScoredDocumentStatement


class TestScoredDocumentStatement(TestCase):
    def setUp(self):
        self.entity_A = ScoredDocumentEntity(entity_type="AT", entity_id="A")
        self.entity_B = ScoredDocumentEntity(entity_type="BT", entity_id="B")
        self.entity_C = ScoredDocumentEntity(entity_type="CT", entity_id="C")
        self.entity_D = ScoredDocumentEntity(entity_type="DT", entity_id="D")

    def test_has_equal_entities(self):
        stmt1 = ScoredDocumentStatement(subject=self.entity_A, relation="r1", object=self.entity_B)
        stmt2 = ScoredDocumentStatement(subject=self.entity_B, relation="r1", object=self.entity_A)
        # Check that statements with swapped entities are considered equal
        self.assertTrue(stmt1.has_equal_entities(stmt2))

        stmt3 = ScoredDocumentStatement(subject=self.entity_C, relation="r1", object=self.entity_A)
        # Check that statements with different entities are not equal
        self.assertFalse(stmt1.has_equal_entities(stmt3))

    def test_has_overlapping_entities(self):
        stmt1 = ScoredDocumentStatement(subject=self.entity_A, relation="r1", object=self.entity_B)
        stmt2 = ScoredDocumentStatement(subject=self.entity_A, relation="r2", object=self.entity_C)
        # Check that statements with a shared entity overlap
        self.assertTrue(stmt1.has_overlapping_entities(stmt2))

        stmt3 = ScoredDocumentStatement(subject=self.entity_D, relation="r2", object=self.entity_C)
        # Check that statements with no shared entity do not overlap
        self.assertFalse(stmt1.has_overlapping_entities(stmt3))


class TestIndexedDocument(TestCase):
    def setUp(self):
        self.tags = [
            TaggedEntity(document=1, ent_id="A", ent_type="AT", start=0, end=5),
            TaggedEntity(document=1, ent_id="A", ent_type="AT", start=10, end=15),
            TaggedEntity(document=1, ent_id="B", ent_type="BT", start=20, end=25)
        ]

        self.statements = [
            StatementExtraction(subject_id="A", subject_type="AT", subject_str="AS",
                                predicate="", relation="r1",
                                object_id="B", object_type="BT", object_str="BS",
                                sentence_id=1, confidence=0.6),
            StatementExtraction(subject_id="A", subject_type="AT", subject_str="AS",
                                predicate="", relation="r1",
                                object_id="B", object_type="BT", object_str="BS",
                                sentence_id=2, confidence=0.9),
            StatementExtraction(subject_id="A", subject_type="AT", subject_str="AS",
                                predicate="", relation="r2",
                                object_id="B", object_type="BT", object_str="BS",
                                sentence_id=3, confidence=0.7)
        ]

        self.narrative_doc = NarrativeDocument(document_id=1,
                                               title="Test Document",
                                               abstract="This is a test abstract.",
                                               metadata=None,
                                               tags=self.tags,
                                               extracted_statements=self.statements)

        self.indexed_doc = IndexedDocument(self.narrative_doc, "TestCollection")

    def test_entity_scoring(self):
        entity_A_key = get_unique_entity_key(entity_type="AT", entity_id="A")
        entity_B_key = get_unique_entity_key(entity_type="BT", entity_id="B")
        scored_entity_A = self.indexed_doc.entity_key2scored_entity[entity_A_key]
        scored_entity_B = self.indexed_doc.entity_key2scored_entity[entity_B_key]

        # Check frequency for entity A is 2
        self.assertEqual(scored_entity_A.tf, 2)
        # Check frequency for entity B is 1
        self.assertEqual(scored_entity_B.tf, 1)

        # Check normalized frequency for A is 1.0 (max frequency is 2)
        self.assertAlmostEqual(scored_entity_A.tf_normalized, 1.0)
        # Check normalized frequency for B is 0.5
        self.assertAlmostEqual(scored_entity_B.tf_normalized, 0.5)

        text_len = len(self.indexed_doc.get_text_content(sections=True))
        expected_coverage_A = (15 - 0) / text_len
        # Check that coverage for entity A is correctly calculated
        self.assertAlmostEqual(scored_entity_A.coverage, expected_coverage_A)

    def test_statement_confidence_selection(self):
        scored_statements = list(self.indexed_doc.scored_statements)
        # Check that there are 2 unique scored statements
        self.assertEqual(len(scored_statements), 2)

        # Check that r1 has the highest confidence (0.9) and r2 has confidence 0.7
        for stmt in scored_statements:
            if stmt.relation == "r1":
                self.assertEqual(stmt.confidence, 0.9)
            elif stmt.relation == "r2":
                self.assertEqual(stmt.confidence, 0.7)

        # Check that each extracted statement is present in the mapping
        for extraction in self.statements:
            self.assertIn(extraction, self.indexed_doc.extracted_stmt2scored_statement)

    def test_all_input_data_taken_over(self):
        # Check that all tags are retained in the NarrativeDocument
        self.assertEqual(len(self.narrative_doc.tags), len(self.tags))
        # Check that all extracted statements are retained in the NarrativeDocument
        self.assertEqual(len(self.narrative_doc.extracted_statements), len(self.statements))
        # Check that at least one scored statement exists in the IndexedDocument
        self.assertGreater(len(self.indexed_doc.scored_statements), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
