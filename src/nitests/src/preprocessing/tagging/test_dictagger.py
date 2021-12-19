import unittest

import narrant.pubtator.document as doc
from narrant.preprocessing.enttypes import DRUG
from narrant.preprocessing.tagging.dictagger import split_indexed_words, DictTagger
from narrant.preprocessing.pharmacy.dosage import DosageFormTagger
from narrant.preprocessing.pharmacy.drug import DrugTagger
from narrant.preprocessing.tagging.vocabulary import expand_vocabulary_term
from narrant.pubtator.extract import read_tagged_documents
from nitests.util import create_test_kwargs, get_test_resource_filepath, resource_rel_path


class TestDictagger(unittest.TestCase):

    def test_exand_vocab_terms(self):
        self.assertIn('ontologies', expand_vocabulary_term('ontology'))
        self.assertIn('ontologys', expand_vocabulary_term('ontology'))
        self.assertIn('ontology', expand_vocabulary_term('ontology'))

        self.assertIn('color', expand_vocabulary_term('colour'))
        self.assertIn('colours', expand_vocabulary_term('colour'))

    def test_tag(self):
        tagger = DosageFormTagger(**create_test_kwargs())
        tagger.desc_by_term = {
            "protein": {"Desc1"},
            "proteins": {"Desc1"},
            "phorbol": {"Desc2", "Desc3"},
            "protein secretion": {"Desc4"},
            "protein synthesis": {"Desc5"}
        }

        doc_to_tags = list(read_tagged_documents(get_test_resource_filepath("infiles/test_dictagger")))
        tag_strings = []
        for d in doc_to_tags:
            tagger.tag_doc(d)
            for tag in d.tags:
                tag_strings.append(repr(tag))

        self.assertIn("<Entity 0,8,proteins,DosageForm,Desc1>", tag_strings)
        self.assertIn("<Entity 1104,1112,proteins,DosageForm,Desc1>", tag_strings)
        self.assertIn("<Entity 1104,1112,proteins,DosageForm,Desc1>", tag_strings)
        self.assertIn("<Entity 1609,1626,protein secretion,DosageForm,Desc4>", tag_strings)

    def test_abbreviation_check(self):
        tagger = DrugTagger(**create_test_kwargs())
        tagger.desc_by_term = {
            "aspirin": {"Desc1"},
            "asa": {"Desc1"},
        }

        doc_to_tags = list(read_tagged_documents(get_test_resource_filepath("infiles/test_dictagger")))
        tag_strings = []
        for d in doc_to_tags:
            tagger.tag_doc(d)
            for tag in d.tags:
                tag_strings.append(repr(tag))

        self.assertIn("<Entity 21,28,aspirin,Drug,Desc1>", tag_strings)
        self.assertIn("<Entity 30,33,asa,Drug,Desc1>", tag_strings)
        self.assertIn("<Entity 52,55,asa,Drug,Desc1>", tag_strings)

    def test_abbreviation_not_allowed_check(self):
        tagger = DrugTagger(**create_test_kwargs())
        tagger.desc_by_term = {
            "aspirin": {"Desc1"},
            "asa": {"Desc1"},
            "metformin": {"Desc2"}
        }

        doc_to_tags = list(read_tagged_documents(resource_rel_path("infiles/test_dictagger/abbreviation_test_not_allowed.txt")))
        tag_strings = []
        for d in doc_to_tags:
            tagger.tag_doc(d)
            for tag in d.tags:
                tag_strings.append(repr(tag))

        self.assertIn("<Entity 52,61,metformin,Drug,Desc2>", tag_strings)
        self.assertNotIn("ASA", tag_strings)

    def test_split_indexed_words(self):
        content = "This is a water-induced, foobar carbon-copper:"
        indexed = split_indexed_words(content)
        self.assertIn(('water-induced', 10), indexed)
        self.assertIn(('water', 10), indexed)
        self.assertIn(('carbon-copper', 32), indexed)
        self.assertNotIn(('carbon', 32), indexed)

    def test_clean_abbreviations(self):
        ent1 = doc.TaggedEntity(document=1, start=0, end=1, text="AB", ent_type="Drug", ent_id="A")
        not_ent1_full = doc.TaggedEntity(document=1, start=0, end=6, text="ABCDEF", ent_type="Drug", ent_id="B")

        should_be_cleaned_1 = [ent1]
        self.assertEqual(0, len(DictTagger.clean_abbreviation_tags(should_be_cleaned_1)))

        should_be_cleaned_2 = [ent1, not_ent1_full]
        self.assertEqual([not_ent1_full], DictTagger.clean_abbreviation_tags(should_be_cleaned_2))

        ent1_full = doc.TaggedEntity(document=1, start=0, end=6, text="ABCDEF", ent_type="Drug", ent_id="A")
        should_not_be_cleaned = [ent1, ent1_full]
        self.assertEqual(should_not_be_cleaned, DictTagger.clean_abbreviation_tags(should_not_be_cleaned))

    def test_text_tagging_simvastatin(self):
        text = "Simvastatin (ST) is a drug. Simvastatin is cool. Cool is also simVAStatin. ST is simvastatine."
        tagger = DrugTagger(**create_test_kwargs())
        tagger.desc_by_term = {
            "simvastatin": {"d1"},
            "simvastatine": {"d1"}
        }

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(6, len(doc1.tags))
        positions = [(0, 11), (13, 15), (28, 39), (62, 73), (75, 77), (81, 93)]

        for idx, tag in enumerate(doc1.tags):
            self.assertEqual(DRUG, tag.ent_type)
            self.assertEqual("d1", tag.ent_id)
            self.assertEqual(positions[idx][0], tag.start)
            self.assertEqual(positions[idx][1], tag.end)

    def test_text_tagging_simvastatin_title_abstract(self):
        title = "Simvastatin (ST) is a drug."
        abstract = "Simvastatin is cool. Cool is also simVAStatin. ST is simvastatine."
        tagger = DrugTagger(**create_test_kwargs())
        tagger.desc_by_term = {
            "simvastatin": {"d1"},
            "simvastatine": {"d1"}
        }

        doc1 = doc.TaggedDocument(title=title, abstract=abstract, id=1)
        tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(6, len(doc1.tags))
        positions = [(0, 11), (13, 15), (28, 39), (62, 73), (75, 77), (81, 93)]

        for idx, tag in enumerate(doc1.tags):
            self.assertEqual(DRUG, tag.ent_type)
            self.assertEqual("d1", tag.ent_id)
            self.assertEqual(positions[idx][0], tag.start)
            self.assertEqual(positions[idx][1], tag.end)

    def test_text_tagging_long_entities(self):
        title = "complex disease"
        tagger = DrugTagger(**create_test_kwargs())
        tagger.desc_by_term = {
            "complex disease": {"d1"},
            "disease": {"d2"}
        }

        doc1 = doc.TaggedDocument(title=title, abstract="", id=1)
        tagger.tag_doc(doc1)
        self.assertEqual(2, len(doc1.tags))

        # now the smaller tag should be removed
        doc1.clean_tags()
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(15, tag.end)
        self.assertEqual("d1", tag.ent_id)
        self.assertEqual(DRUG, tag.ent_type)


if __name__ == '__main__':
    unittest.main()
