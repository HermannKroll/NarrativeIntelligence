import json
from unittest import TestCase

from sqlalchemy import delete

from kgextractiontoolbox.backend.models import Document, Sentence, Predication, Tag
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex
from narraint.queryengine.index.compute_reverse_index_tag import compute_inverted_index_for_tags


class ReverseTagIdxTest(TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()

        stmt = delete(TagInvertedIndex)
        session.execute(stmt)
        session.commit()

        stmt = delete(Tag)
        session.execute(stmt)
        session.commit()


        document_values = [dict(id=1, collection="IDX_INVERTED_TAG", title="Test", abstract="Test Abstract"),
                           dict(id=2, collection="IDX_INVERTED_TAG", title="Test", abstract="Test Abstract")]
        sentences_values = [dict(id=1, document_collection="IDX_INVERTED_TAG", text="ABC", md5hash="HASH")]
        pred_values = [dict(id=100000, document_id=1, document_collection="IDX_INVERTED_TAG",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=100001, document_id=1, document_collection="IDX_INVERTED_TAG",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t2", relation="T2",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test")]

        tag_values = [dict(id=100000, ent_type="AT", ent_id="A", ent_str="AS", start=0, end=0,
                           document_id=1, document_collection="IDX_INVERTED_TAG")]

        Document.bulk_insert_values_into_table(session, document_values)
        Sentence.bulk_insert_values_into_table(session, sentences_values)
        Predication.bulk_insert_values_into_table(session, pred_values)
        Tag.bulk_insert_values_into_table(session, tag_values)



    def test_full_reverse_idx(self):
        compute_inverted_index_for_tags()

        session = SessionExtended.get()
        self.assertEqual(1, session.query(TagInvertedIndex).count())

        allowed_keys = [("A", "AT", "IDX_INVERTED_TAG")]
        allowed_doc_ids = [[1]]

        db_rows = {}
        for row in session.query(TagInvertedIndex):
            key = (row.entity_id, row.entity_type, row.document_collection)
            self.assertIn(key, allowed_keys)
            db_rows[key] = json.loads(row.document_ids)

        self.assertEqual(allowed_doc_ids[0], db_rows[allowed_keys[0]])
        
        
    def test_full_reverse_idx_support(self):
        compute_inverted_index_for_tags()

        session = SessionExtended.get()
        self.assertEqual(1, session.query(TagInvertedIndex).count())

        allowed_keys = [("A", "AT", "IDX_INVERTED_TAG")]
        for row in session.query(TagInvertedIndex):
            key = (row.entity_id, row.entity_type, row.document_collection)
            self.assertIn(key, allowed_keys)
            self.assertEqual(1, row.support)



    def test_full_reverse_idx_delta_mode(self):
        session = SessionExtended.get()
        compute_inverted_index_for_tags()

        tag_values = [
            dict(id=100001, ent_type="AT", ent_id="A", ent_str="AS", start=0, end=0,
                 document_id=2, document_collection="IDX_INVERTED_TAG"),
            dict(id=100002, ent_type="BT", ent_id="B", ent_str="BS", start=0, end=0,
                 document_id=2, document_collection="IDX_INVERTED_TAG")
        ]
        Tag.bulk_insert_values_into_table(session, tag_values)

        pred_values = [dict(id=100004, document_id=2, document_collection="IDX_INVERTED_TAG",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t3", relation="T3",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test")
                       ]
        Predication.bulk_insert_values_into_table(session, pred_values)

        compute_inverted_index_for_tags(predication_id_min=100004)
        self.assertEqual(2, session.query(TagInvertedIndex).count())

        allowed_keys = [("A", "AT", "IDX_INVERTED_TAG"), ("B", "BT", "IDX_INVERTED_TAG")]
        allowed_doc_ids = [[2, 1], [2]]

        db_rows = {}
        for row in session.query(TagInvertedIndex):
            key = (row.entity_id, row.entity_type, row.document_collection)
            self.assertIn(key, allowed_keys)
            db_rows[key] = (json.loads(row.document_ids), row.support)

            # support must correspond to the number of documents
            self.assertEquals(row.support, len(db_rows[key])[0])

        # Check keys
        self.assertEqual(allowed_doc_ids[0], db_rows[allowed_keys[0]][0])
        self.assertEqual(allowed_doc_ids[1], db_rows[allowed_keys[1]][0])

        # Check support
        self.assertEqual(1, db_rows[allowed_keys[0]][1])
        self.assertEqual(1, db_rows[allowed_keys[1]][1])
