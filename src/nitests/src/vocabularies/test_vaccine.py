import unittest

from narrant.preprocessing.enttypes import VACCINE
from narrant.preprocessing.pharmacy.vaccine import VaccineTagger
from narrant.pubtator.document import TaggedDocument
from nitests.util import create_test_kwargs


class TestVaccineVocabulary(unittest.TestCase):

    def setUp(self) -> None:
        self.tagger = VaccineTagger(**create_test_kwargs())
        self.tagger.prepare()

    def test_mesh_vaccince(self):
        text = "Oxford-AstraZeneca COVID Vaccine is novel."
        doc = TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc)
        doc.clean_tags()
        doc.sort_tags()

        self.assertEqual(1, len(doc.tags))
        t = doc.tags[0]
        self.assertEqual('MESH:D000090985', t.ent_id)
        self.assertEqual(0, t.start)
        self.assertEqual(32, t.end)
        self.assertEqual(VACCINE, t.ent_type)

    def test_wikidata_vaccince(self):
        text = "CIGB-66 is novel."
        doc = TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc)
        doc.clean_tags()
        doc.sort_tags()

        self.assertEqual(1, len(doc.tags))
        t = doc.tags[0]
        self.assertEqual('Q106390652', t.ent_id)
        self.assertEqual(0, t.start)
        self.assertEqual(7, t.end)
        self.assertEqual(VACCINE, t.ent_type)

    def test_wikidata_mapped_to_mesh_vaccince(self):
        text = "corona vaccine is novel."
        doc = TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc)
        doc.clean_tags()
        doc.sort_tags()

        self.assertEqual(1, len(doc.tags))
        t = doc.tags[0]
        self.assertEqual('MESH:D000086663', t.ent_id)
        self.assertEqual(0, t.start)
        self.assertEqual(14, t.end)
        self.assertEqual(VACCINE, t.ent_type)
