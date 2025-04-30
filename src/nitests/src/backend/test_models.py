import unittest

from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex


class TestModels(unittest.TestCase):

    def test_tag_inverted_index(self):
        session = SessionExtended.get()

        stmt = delete(TagInvertedIndex)
        session.execute(stmt)
        session.commit()

        table_rows = [
            dict(entity_id="A", entity_type="TYPE_A", document_collection="Test", support=5,
                 document_ids="[1,2,3,4,5]"),
            dict(entity_id="B", entity_type="TYPE_B", document_collection="Test", support=5,
                 document_ids="[6,7,8,9,10]"),
            dict(entity_id="C", entity_type="TYPE_C", document_collection="Test", support=5,
                 document_ids="[11]")
        ]

        TagInvertedIndex.bulk_insert_values_into_table(session, table_rows)

        collection2doc_ids = TagInvertedIndex.retrieve_document_ids_for_entity(session, entity_id="A", 
                                                                             entity_type="TYPE_A")
        self.assertEqual(1, len(collection2doc_ids))
        doc_ids = collection2doc_ids['Test']
        self.assertEqual(5, len(doc_ids))
        self.assertEqual({1, 2, 3, 4, 5}, doc_ids)

        collection2doc_ids = TagInvertedIndex.retrieve_document_ids_for_entity(session, entity_id="A",
                                                                               entity_type="TYPE_A",
                                                                               document_collections=["Test"])
        self.assertEqual(1, len(collection2doc_ids))
        doc_ids = collection2doc_ids['Test']
        self.assertEqual(5, len(doc_ids))
        self.assertEqual({1, 2, 3, 4, 5}, doc_ids)

        collection2doc_ids = TagInvertedIndex.retrieve_document_ids_for_entity(session, entity_id="A",
                                                                               entity_type="TYPE_A",
                                                                               document_collections=["NOT_EXISTS"])
        self.assertEqual(0, len(collection2doc_ids))

        collection2doc_ids = TagInvertedIndex.retrieve_document_ids_for_entity(session, entity_id="B",
                                                                             entity_type="TYPE_B")
        self.assertEqual(1, len(collection2doc_ids))
        doc_ids = collection2doc_ids['Test']
        self.assertEqual(5, len(doc_ids))
        self.assertEqual({6, 7, 8, 9, 10}, doc_ids)

        collection2doc_ids = TagInvertedIndex.retrieve_document_ids_for_entity(session, entity_id="C",
                                                                             entity_type="TYPE_C")
        self.assertEqual(1, len(collection2doc_ids))
        doc_ids = collection2doc_ids['Test']
        self.assertEqual(1, len(doc_ids))
        self.assertEqual({11}, doc_ids)


        collection2doc_ids = TagInvertedIndex.retrieve_document_ids_for_entities(session, entity_ids=["A", "B"],
                                                                      entity_types=["TYPE_A", "TYPE_B"])
        self.assertEqual(1, len(collection2doc_ids))
        doc_ids = collection2doc_ids['Test']
        self.assertEqual(10, len(doc_ids))
        self.assertEqual({1, 2, 3, 4, 5, 6, 7, 8, 9, 10}, doc_ids)
