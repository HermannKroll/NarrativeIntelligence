import ast
from unittest import TestCase

from sqlalchemy import delete

from kgextractiontoolbox.backend.models import Document, Sentence, Predication
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex
from narraint.queryengine.index.compute_reverse_index_predication import denormalize_predication_table


class ReversePredicationIdxText(TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()

        stmt = delete(PredicationInvertedIndex)
        session.execute(stmt)
        session.commit()

        stmt = delete(Predication)
        session.execute(stmt)
        session.commit()

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

    def test_full_reverse_idx_low_memory(self):
        denormalize_predication_table(low_memory=True, buffer_size=1)

        session = SessionExtended.get()
        self.assertEqual(2, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT")]
        allowed_pm = ['[1]']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.document_ids
            self.assertIn(row.document_collection, ["RIDXTEST"])
            self.assertEqual(row.support, len(row.document_ids.split(",")))

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[1]])

    @staticmethod
    def prepare_buffer_size_tests(session):
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

    def test_full_reverse_idx_low_memory_buffer1(self):
        session = SessionExtended.get()
        self.prepare_buffer_size_tests(session)

        denormalize_predication_table(low_memory=True, buffer_size=1)
        self.assertEqual(3, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT"), ("A", "AT", "T3", "B", "BT")]
        allowed_pm = ['[2,1]', '[1]', '[2]']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.document_ids
            self.assertIn(row.document_collection, ["RIDXTEST"])
            self.assertEqual(row.support, len(row.document_ids.split(",")))

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[1], db_rows[allowed_keys[1]])
        self.assertEqual(allowed_pm[2], db_rows[allowed_keys[2]])

    def test_full_reverse_idx_low_memory_buffer2(self):
        session = SessionExtended.get()
        self.prepare_buffer_size_tests(session)

        denormalize_predication_table(low_memory=True, buffer_size=2)
        self.assertEqual(3, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT"), ("A", "AT", "T3", "B", "BT")]
        allowed_pm = ['[2,1]', '[1]', '[2]']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.document_ids
            self.assertIn(row.document_collection, ["RIDXTEST"])
            self.assertEqual(row.support, len(row.document_ids.split(",")))

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[1], db_rows[allowed_keys[1]])
        self.assertEqual(allowed_pm[2], db_rows[allowed_keys[2]])

    def test_full_reverse_idx_low_memory_buffer3(self):
        session = SessionExtended.get()
        self.prepare_buffer_size_tests(session)

        denormalize_predication_table(low_memory=True, buffer_size=3)
        self.assertEqual(3, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT"), ("A", "AT", "T3", "B", "BT")]
        allowed_pm = ['[2,1]', '[1]', '[2]']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.document_ids
            self.assertIn(row.document_collection, ["RIDXTEST"])
            self.assertEqual(row.support, len(row.document_ids.split(",")))

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[1], db_rows[allowed_keys[1]])
        self.assertEqual(allowed_pm[2], db_rows[allowed_keys[2]])

    def test_full_reverse_idx_low_memory_buffer1000(self):
        session = SessionExtended.get()
        self.prepare_buffer_size_tests(session)

        denormalize_predication_table(low_memory=True, buffer_size=1000)
        self.assertEqual(3, session.query(PredicationInvertedIndex).count())

        allowed_keys = [("A", "AT", "T1", "B", "BT"), ("A", "AT", "T2", "B", "BT"), ("A", "AT", "T3", "B", "BT")]
        allowed_pm = ['[2,1]', '[1]', '[2]']

        db_rows = {}
        for row in session.query(PredicationInvertedIndex):
            key = (row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type)
            self.assertIn(key, allowed_keys)
            db_rows[key] = row.document_ids
            self.assertIn(row.document_collection, ["RIDXTEST"])
            self.assertEqual(row.support, len(row.document_ids.split(",")))

        self.assertEqual(allowed_pm[0], db_rows[allowed_keys[0]])
        self.assertEqual(allowed_pm[1], db_rows[allowed_keys[1]])
        self.assertEqual(allowed_pm[2], db_rows[allowed_keys[2]])
