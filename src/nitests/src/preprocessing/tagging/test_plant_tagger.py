import unittest

import narrant.pubtator.document as doc
from narrant.preprocessing.enttypes import PLANT_FAMILY_GENUS
from narrant.preprocessing.pharmacy.plantfamilygenus import PlantFamilyGenusTagger
from nitests.util import create_test_kwargs


class TestPlantTagger(unittest.TestCase):

    def setUp(self) -> None:
        self.tagger = PlantFamilyGenusTagger(**create_test_kwargs())
        self.tagger.prepare()

    def test_text_tagging_family(self):
        text = "Vitaceae is a wonderful plant."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(8, tag.end)
        self.assertEqual("Vitaceae", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_family_and_genus(self):
        text = "Vitaceae is a wonderful plant. Acacia is it too."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(2, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(8, tag.end)
        self.assertEqual("Vitaceae", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

        tag = doc1.tags[1]
        self.assertEqual(31, tag.start)
        self.assertEqual(37, tag.end)
        self.assertEqual("Acacia", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_genus_without_family(self):
        text = "Bla is a wonderful plant. Acacia is it too."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(0, len(doc1.tags))

    def test_text_tagging_genus_with_plant_rule(self):
        text = "Acacia is used in traditional chinese medicine."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(6, tag.end)
        self.assertEqual("Acacia", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_clean_only_plants(self):
        text = "Bla is a wonderful plant. Acacia is it too."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        doc1.tags.append(doc.TaggedEntity(document=1, start=20, end=24, ent_id="Plant", ent_type="Misc",
                                          text="plant"))
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(20, tag.start)
        self.assertEqual(24, tag.end)
        self.assertEqual("Plant", tag.ent_id)
        self.assertEqual("Misc", tag.ent_type)
