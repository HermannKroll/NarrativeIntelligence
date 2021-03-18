import unittest
import os

from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.tagging.dictagger import DictTagger, split_indexed_words
from narraint.preprocessing.tagging.dosage import DosageFormTagger
from narraint.preprocessing.tagging.drug import DrugTagger
from narraint.preprocessing.tagging.vocabularies import expand_vocabulary_term
from narraint.tools import proj_rel_path
from nitests.util import make_test_tempdir, create_test_kwargs, get_test_resource_filepath
import narraint.entity.enttypes as enttypes
import narraint.pubtator.document as doc


class TestDictagger(unittest.TestCase):

    def test_exand_vocab_terms(self):
        self.assertIn('ontologies', expand_vocabulary_term('ontology'))
        self.assertIn('ontologys', expand_vocabulary_term('ontology'))
        self.assertIn('ontology', expand_vocabulary_term('ontology'))

        self.assertIn('color', expand_vocabulary_term('colour'))
        self.assertIn('colours', expand_vocabulary_term('colour'))

    def test_tag(self):
        out_file = proj_rel_path("nitests/tmp/MC1313813Tagged.txt")
        tagger = DosageFormTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "protein": {"Desc1"},
            "proteins": {"Desc1"},
            "phorbol": {"Desc2", "Desc3"},
            "protein secretion": {"Desc4"},
            "protein synthesis": {"Desc5"}
        }
        tagger._tag(proj_rel_path("nitests/resources/infiles/test_dictagger/PMC1313813Untagged.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        document = doc.TaggedDocument(in_file=out_file)
        # document.clean_tags()
        self.assertTrue(document)
        strings = [repr(tag) for tag in document.tags]
        self.assertIn("<Entity 0,8,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1104,1112,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1104,1112,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1609,1626,protein secretion,DosageForm,Desc4>", strings)

    def test_abbreviation_check(self):
        out_file = proj_rel_path("nitests/tmp/abbreviation_test_allowed.txt")
        tagger = DrugTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "aspirin": {"Desc1"},
            "asa": {"Desc1"},
        }
        tagger._tag(proj_rel_path("nitests/resources/infiles/test_dictagger/abbreviation_test_allowed.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        document = doc.parse_tag_list(out_file)
        self.assertTrue(document)
        strings = [repr(tag) for tag in document]
        self.assertIn("<Entity 21,28,aspirin,Drug,Desc1>", strings)
        self.assertIn("<Entity 30,33,asa,Drug,Desc1>", strings)
        self.assertIn("<Entity 52,55,asa,Drug,Desc1>", strings)

    def test_abbreviation_not_allowed_check(self):
        out_file = proj_rel_path("nitests/tmp/abbreviation_test_not_allowed.txt")
        tagger = DrugTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "aspirin": {"Desc1"},
            "asa": {"Desc1"},
            "metformin": {"Desc2"}
        }
        tagger._tag(proj_rel_path("nitests/resources/infiles/test_dictagger/abbreviation_test_not_allowed.txt"),
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

    def test_conjunction_product(self):
        tuples = DictTagger.conjunction_product(split_indexed_words("brain, breast and ovarian cancer"))
        desired = "[[('brain', 0), ('ovarian', 18)], [('brain', 0), ('cancer', 26)], [('brain', 0), ('ovarian', 18), " \
                  "('cancer', 26)], [('breast', 7), ('ovarian', 18)], [('breast', 7), ('cancer', 26)], [('breast', 7), " \
                  "('ovarian', 18), ('cancer', 26)], [('brain', 0), ('breast', 7), ('ovarian', 18)], [('brain', 0), " \
                  "('breast', 7), ('cancer', 26)], [('brain', 0), ('breast', 7), ('ovarian', 18), ('cancer', 26)]]"
        self.assertEqual(str(list(tuples)), desired)


if __name__ == '__main__':
    unittest.main()
