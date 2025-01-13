import json
import logging
from unittest import TestCase

from sqlalchemy import delete, insert

from narraint.backend.database import SessionExtended
from narraint.backend.models import EntityTaggerData, IndexVersion
from narraint.frontend.entity.entitytagger_db import EntityTaggerDB

logging.basicConfig(
    filename='test.log',
    filemode='w',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s: %(message)s',
)


def prepare_tagging_index(terms: dict):
    session = SessionExtended.get()
    session.execute(delete(EntityTaggerData))
    session.commit()

    entries = list()
    for k, v in terms.items():
        entries.append(dict(entity_id=v, entity_type="type", entity_class=None, synonym=k))

    EntityTaggerData.bulk_insert_values_into_table(session, entries)
    session.remove()


class EntityTaggerTestCase(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # update current index version
        session = SessionExtended.get()
        session.execute(delete(IndexVersion).where(IndexVersion.name == EntityTaggerDB.NAME))
        session.execute(insert(IndexVersion).values(name=EntityTaggerDB.NAME, version=EntityTaggerDB.VERSION))

    def test_single_terms(self):
        terms = {
            "Codeine": 1,
            "Furosemide": 2,
        }

        prepare_tagging_index(terms)
        entity_tagger = EntityTaggerDB()

        # at least one result
        self.assertGreater(len(entity_tagger.tag_entity('codein')), 0)

        # term partially known
        self.assertEqual(len(entity_tagger.tag_entity('codein')),
                         len(entity_tagger.tag_entity('codeine')))

        self.assertEqual(len(entity_tagger.tag_entity('Codein')),
                         len(entity_tagger.tag_entity('Codeine')))

        # tagger yields the same results
        for ent in entity_tagger.tag_entity('codeine'):
            self.assertIn(ent, entity_tagger.tag_entity('codein'))

        for ent in entity_tagger.tag_entity('Codeine'):
            self.assertIn(ent, entity_tagger.tag_entity('Codein'))

        # test for another term
        self.assertEqual(len(entity_tagger.tag_entity('Furosemid')),
                         len(entity_tagger.tag_entity('Furosemide')))

        for ent in entity_tagger.tag_entity('Furosemide'):
            self.assertIn(ent, entity_tagger.tag_entity('Furosemid'))

        # test word components
        self.assertEqual(len(entity_tagger.tag_entity('semid')),
                         len(entity_tagger.tag_entity('Furo')))

        for ent in entity_tagger.tag_entity('semid'):
            self.assertIn(ent, entity_tagger.tag_entity('Furo'))

    def test_multi_terms(self):
        terms = {
            "Diabetes": 1,
            "Diabetes Mellitus": 2,
            "Diabetes Mellitus, Type I": 3,
            "Diabetes Mellitus, Type 1": 4,
            "Diabetes Mellitus, Type II": 5,
            "Diabetes Mellitus, Type 2": 6,

            "Type 2 Diabetes": 7,
            "Type 2 Diabetes Mellitus": 8
        }

        prepare_tagging_index(terms)
        entity_tagger = EntityTaggerDB()

        # single term (every known term has the word diabetes)
        self.assertEqual(len(entity_tagger.tag_entity('Diabetes')), 8)
        self.assertEqual(len(entity_tagger.tag_entity('diabetes')), 8)

        for ent in entity_tagger.tag_entity('Diabetes'):
            self.assertIn(ent, entity_tagger.tag_entity('diabetes'))

        # two terms (reversed order yield the same results)
        self.assertEqual(len(entity_tagger.tag_entity('Diabetes Mellitus')), 6)
        self.assertEqual(len(entity_tagger.tag_entity('Mellitus Diabetes')), 6)

        for ent in entity_tagger.tag_entity('Diabetes Mellitus'):
            self.assertIn(ent, entity_tagger.tag_entity('Mellitus Diabetes'))

        # two distant terms
        self.assertEqual(len(entity_tagger.tag_entity('Diabetes Type')), 6)
        self.assertEqual(len(entity_tagger.tag_entity('Diabetes II')), 1)

        # multiple word components (chopped off)
        self.assertEqual(len(entity_tagger.tag_entity('Diab Typ 2')), 3)
        self.assertEqual(len(entity_tagger.tag_entity('betes Typ II')), 1)
