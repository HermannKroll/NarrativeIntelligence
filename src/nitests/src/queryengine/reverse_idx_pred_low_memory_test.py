from unittest import TestCase

from sqlalchemy import delete

from kgextractiontoolbox.backend.models import Document, Sentence, Predication
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex
from narraint.queryengine.index.compute_reverse_index_predication import denormalize_predication_table


class ReversePredicationIdxText(TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()
        document_values = [dict(id=1, collection="RIDXTEST", title="Test", abstract="Test Abstract"),
                           dict(id=2, collection="RIDXTEST", title="Test", abstract="Test Abstract")]
        sentences_values = [dict(id=1, document_collection="RIDXTEST", text="ABC", md5hash="HASH")]
        pred_values = [dict(id=1000, document_id=1, document_collection="RIDXTEST",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1001, document_id=1, document_collection="RIDXTEST",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t2", relation="T2",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test")]

        Document.bulk_insert_values_into_table(session, document_values)
        Sentence.bulk_insert_values_into_table(session, sentences_values)
        Predication.bulk_insert_values_into_table(session, pred_values)

        session = SessionExtended.get()
        stmt = delete(PredicationInvertedIndex)
        session.execute(stmt)
        session.commit()

    def test_full_reverse_idx_low_memory(self):
        denormalize_predication_table(consider_metadata=False, low_memory=True)

        session = SessionExtended.get()
        self.assertEqual(2, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT")]
        allowed_pm = ['{"RIDXTEST": {"1": [1000]}}', '{"RIDXTEST": {"1": [1001]}}']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.provenance_mapping

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[1], db_rows[allowed_keys[1]])

    def test_full_reverse_idx_low_memory_delta_mode(self):
        session = SessionExtended.get()
        denormalize_predication_table(consider_metadata=False, low_memory=True)
        pred_values = [dict(id=1002, document_id=1, document_collection="RIDXTEST",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1003, document_id=2, document_collection="RIDXTEST",
                             subject_id="A", subject_type="AT", subject_str="A_STR",
                             predicate="t1", relation="T1",
                             object_id="B", object_type="BT", object_str="B_STR",
                             sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1004, document_id=2, document_collection="RIDXTEST",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t3", relation="T3",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test")
                       ]
        Predication.bulk_insert_values_into_table(session, pred_values)
        denormalize_predication_table(predication_id_min=1002, consider_metadata=False, low_memory=True)
        self.assertEqual(3, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT"), ("A", "AT", "T3", "B", "BT")]
        allowed_pm = ['{"RIDXTEST": {"1": [1000, 1002], "2": [1003]}}', '{"RIDXTEST": {"1": [1001]}}', '{"RIDXTEST": {"2": [1004]}}']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.provenance_mapping

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[1], db_rows[allowed_keys[1]])
        self.assertEqual(allowed_pm[2], db_rows[allowed_keys[2]])