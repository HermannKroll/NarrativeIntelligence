import os
import unittest

import narrant.pubtator.document as doc
from narrant.preprocessing.tagging.dictagger import split_indexed_words
from narrant.preprocessing.tagging.dosage import DosageFormTagger
from narrant.preprocessing.tagging.drug import DrugTagger
from narrant.preprocessing.tagging.vocabularies import expand_vocabulary_term
from nitests.util import create_test_kwargs, get_test_resource_filepath, tmp_rel_path, \
    resource_rel_path


class TestDictagger(unittest.TestCase):

    def test_exand_vocab_terms(self):
        self.assertIn('ontologies', expand_vocabulary_term('ontology'))
        self.assertIn('ontologys', expand_vocabulary_term('ontology'))
        self.assertIn('ontology', expand_vocabulary_term('ontology'))

        self.assertIn('color', expand_vocabulary_term('colour'))
        self.assertIn('colours', expand_vocabulary_term('colour'))

    def test_tag(self):
        out_file = tmp_rel_path("MC1313813Tagged.txt")
        tagger = DosageFormTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "protein": {"Desc1"},
            "proteins": {"Desc1"},
            "phorbol": {"Desc2", "Desc3"},
            "protein secretion": {"Desc4"},
            "protein synthesis": {"Desc5"}
        }
        tagger._tag(resource_rel_path("infiles/test_dictagger/PMC1313813Untagged.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        content = ""
        with open(out_file, 'rt') as f:
            content = f.read()
        document = doc.TaggedDocument(content)
        # document.clean_tags()
        self.assertTrue(document)
        strings = [repr(tag) for tag in document.tags]
        self.assertIn("<Entity 0,8,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1104,1112,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1104,1112,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1609,1626,protein secretion,DosageForm,Desc4>", strings)

    def test_abbreviation_check(self):
        out_file = tmp_rel_path("abbreviation_test_allowed.txt")
        tagger = DrugTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "aspirin": {"Desc1"},
            "asa": {"Desc1"},
        }
        tagger._tag(resource_rel_path("infiles/test_dictagger/abbreviation_test_allowed.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        document = doc.parse_tag_list(out_file)
        self.assertTrue(document)
        strings = [repr(tag) for tag in document]
        self.assertIn("<Entity 21,28,aspirin,Drug,Desc1>", strings)
        self.assertIn("<Entity 30,33,asa,Drug,Desc1>", strings)
        self.assertIn("<Entity 52,55,asa,Drug,Desc1>", strings)

    def test_abbreviation_not_allowed_check(self):
        out_file = tmp_rel_path("abbreviation_test_not_allowed.txt")
        tagger = DrugTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "aspirin": {"Desc1"},
            "asa": {"Desc1"},
            "metformin": {"Desc2"}
        }
        tagger._tag(resource_rel_path("infiles/test_dictagger/abbreviation_test_not_allowed.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        document = doc.parse_tag_list(out_file)
        self.assertTrue(document)
        strings = [repr(tag) for tag in document]
        self.assertIn("<Entity 52,61,metformin,Drug,Desc2>", strings)
        self.assertNotIn("ASA", strings)

    def test_split_indexed_words(self):
        content = "This is a water-induced, foobar carbon-copper:"
        indexed = split_indexed_words(content)
        self.assertIn(('water-induced', 10), indexed)
        self.assertIn(('water', 10), indexed)
        self.assertIn(('carbon-copper', 32), indexed)
        self.assertNotIn(('carbon', 32), indexed)


if __name__ == '__main__':
    unittest.main()
