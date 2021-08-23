import unittest

from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, Sentence, Predication
from narraint.cleaning.check_type_constraints import delete_predications_hurting_type_constraints
from narraint.cleaning.relation_type_constraints import RelationTypeConstraintStore
from nitests import util


class RelationTypeConstraintChecking(unittest.TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()
        documents = [dict(id=1, collection="Test", title="ABC", abstract=""),
                     dict(id=2, collection="Test", title="DEF", abstract="")]
        Document.bulk_insert_values_into_table(session, documents)

        sentences = [dict(id=1, document_id=1, document_collection="Test", text="Hello", md5hash="1"),
                     dict(id=2, document_id=1, document_collection="Test", text="World", md5hash="2")]
        Sentence.bulk_insert_values_into_table(session, sentences)

        predications = [dict(id=1,
                             document_id=1, document_collection="Test",
                             subject_id="A", subject_type="Drug", subject_str="",
                             predicate="treats", predicate_canonicalized="treats",
                             object_id="B", object_type="Disease", object_str="",
                             sentence_id=1, extraction_type="PathIE"),
                        dict(id=2,
                             document_id=1, document_collection="Test",
                             subject_id="A", subject_type="Disease", subject_str="",
                             predicate="treats", predicate_canonicalized="treats",
                             object_id="B", object_type="Disease", object_str="",
                             sentence_id=1, extraction_type="PathIE"),
                        dict(id=3,
                             document_id=2, document_collection="Test",
                             subject_id="A", subject_type="Disease", subject_str="",
                             predicate="induces", predicate_canonicalized="induces",
                             object_id="B", object_type="Disease", object_str="",
                             sentence_id=2, extraction_type="PathIE"),
                        dict(id=4,
                             document_id=2, document_collection="Test",
                             subject_id="A", subject_type="Gene", subject_str="",
                             predicate="induces", predicate_canonicalized="induces",
                             object_id="B", object_type="Gene", object_str="",
                             sentence_id=2, extraction_type="PathIE")
                        ]
        Predication.bulk_insert_values_into_table(session, predications)

    def test_check_constraints(self):
        store = RelationTypeConstraintStore()
        store.load_from_json(util.get_test_resource_filepath('cleaning/pharm_relation_type_constraints.json'))

        delete_predications_hurting_type_constraints(store, "Test")

        session = SessionExtended.get()
        self.assertIsNotNone(session.query(Predication).filter(Predication.id == 1).first())
        self.assertIsNone(session.query(Predication).filter(Predication.id == 2).first())
        self.assertIsNotNone(session.query(Predication).filter(Predication.id == 3).first())
        self.assertIsNone(session.query(Predication).filter(Predication.id == 4).first())