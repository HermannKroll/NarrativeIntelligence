from unittest import TestCase

from sqlalchemy import delete

from kgextractiontoolbox.backend.models import Predication, Sentence
from narraint.backend.database import SessionExtended
from narraint.backend.models import Document
from narraint.keywords2graph.schema_support_graph import SchemaSupportGraph


class SchemaSupportGraphTest(TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()

        stmt = delete(Predication)
        session.execute(stmt)
        session.commit()

        document_values = [dict(id=1, collection="schemagraph", title="Test", abstract="Test Abstract"),
                           dict(id=2, collection="schemagraph", title="Test", abstract="Test Abstract"),
                           dict(id=3, collection="schemagraph", title="Test", abstract="Test Abstract"),
                           dict(id=4, collection="schemagraph", title="Test", abstract="Test Abstract")]
        sentences_values = [dict(id=1, document_collection="schemagraph", text="ABC", md5hash="HASH")]
        pred_values = [dict(id=1000, document_id=1, document_collection="schemagraph",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1001, document_id=1, document_collection="schemagraph",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1002, document_id=2, document_collection="schemagraph",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1003, document_id=3, document_collection="schemagraph",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T1",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),

                       dict(id=1004, document_id=2, document_collection="schemagraph",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T2",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),
                       dict(id=1005, document_id=3, document_collection="schemagraph",
                            subject_id="A", subject_type="AT", subject_str="A_STR",
                            predicate="t1", relation="T2",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test"),

                       dict(id=1006, document_id=4, document_collection="schemagraph",
                            subject_id="A", subject_type="AT_X", subject_str="A_STR",
                            predicate="t1", relation="T5",
                            object_id="B", object_type="BT", object_str="B_STR",
                            sentence_id=1, confidence=1.0, extraction_type="Test")
                       ]

        Document.bulk_insert_values_into_table(session, document_values)
        Sentence.bulk_insert_values_into_table(session, sentences_values)
        Predication.bulk_insert_values_into_table(session, pred_values)

        SchemaSupportGraph.compute_schema_graph()

    def test_schema_graph_based_on_predications(self):
        sg: SchemaSupportGraph = SchemaSupportGraph()
        self.assertEqual(3, sg.get_support("AT", "T1", "BT"))
        self.assertEqual(2, sg.get_support("AT", "T2", "BT"))
        self.assertEqual(1, sg.get_support("AT_X", "T5", "BT"))

        relation_dict = sg.get_relations_between("AT", "BT")
        self.assertIn("T1", relation_dict)
        self.assertIn("T2", relation_dict)

        self.assertEqual(3, relation_dict["T1"])
        self.assertEqual(2, relation_dict["T2"])

        relation_dict = sg.get_relations_between("AT_X", "BT")
        self.assertIn("T5", relation_dict)

        self.assertEqual(1, relation_dict["T5"])

    def test_schema_graph_no_support_values(self):
        SchemaSupportGraph.compute_schema_graph()

        sg: SchemaSupportGraph = SchemaSupportGraph()
        self.assertEqual(0, sg.get_support("AT_N", "T1", "BT"))
        self.assertEqual(0, sg.get_support("AT_N", "T2", "BT"))
        self.assertEqual(0, sg.get_support("AT_X_N", "T5", "BT"))

        self.assertEqual(0, sg.get_support("AT", "T1_N", "BT"))
        self.assertEqual(0, sg.get_support("AT", "T2_N", "BT"))
        self.assertEqual(0, sg.get_support("AT_X", "T5_N", "BT"))

        self.assertEqual(0, sg.get_support("AT", "T1", "BT_N"))
        self.assertEqual(0, sg.get_support("AT", "T2", "BT_N"))
        self.assertEqual(0, sg.get_support("AT_X", "T5", "BT_N"))
