import os
import unittest
import filecmp

import pytest

from narraint.preprocessing.tagging.metadictagger import MetaDicTaggerFactory, MetaDicTagger
import narraint.entity.enttypes as et
import nitests.util as util
from narraint import tools
from narraint.pubtator.document import parse_tag_list, TaggedEntity
from narraint.pubtator.extract import read_tagged_documents


class TestMetadictagger(unittest.TestCase):
    ent_type_set = {et.DRUG, et.EXCIPIENT, et.DOSAGE_FORM, et.PLANT_FAMILY}

    def test_init(self):
        metatag = TestMetadictagger.make_metatag()
        self.assertSetEqual(set(metatag._vocabs.keys()), TestMetadictagger.ent_type_set)
        self.assertIn("MESH:D007267", metatag._vocabs[et.DOSAGE_FORM]["injection"])
        self.assertIn("Agave", metatag._vocabs[et.PLANT_FAMILY]["agave"])
        self.assertIn("DB06727", metatag._vocabs[et.DRUG]["sparteine"])

        # self.assertEqual(True, False)

    def test_tag(self):

        in_1 = util.get_test_resource_filepath("infiles/test_metadictagger/4297.txt")
        out_1 = tools.proj_rel_path("nitests/tmp/out/4297.txt")
        os.makedirs(os.path.dirname(out_1))
        in_2 = util.get_test_resource_filepath("infiles/test_metadictagger/5600.txt")
        out_2 = tools.proj_rel_path("nitests/tmp/out/5600.txt")
        metatag = TestMetadictagger.make_metatag()
        metatag._tag(in_1, out_1)
        metatag._tag(in_2, out_2)
        tags_1 = [repr(tag) for tag in parse_tag_list(out_1)]
        tags_2 = [repr(tag) for tag in parse_tag_list(out_2)]

        assert_tags_pmc_4297_5600(self, tags_1, tags_2)

    def test_custom_abbreviation(self):
        in_file = util.get_test_resource_filepath("infiles/test_metadictagger/abbreviations.txt")
        metatag = TestMetadictagger.make_metatag()
        out_file = metatag.tag_doc([d for d in read_tagged_documents(in_file)][0])
        out_file.clean_tags()
        self.assertIn(TaggedEntity(None, 32926486, 709, 712, "eo", "Excipient", "Ethylene oxide"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926486, 1227, 1230, "eo", "Excipient", "Ethylene oxide"), out_file.tags)



    @staticmethod
    def make_metatag():
        factory = MetaDicTaggerFactory(TestMetadictagger.ent_type_set,
                                       util.create_test_kwargs(
                                           util.get_test_resource_filepath("infiles/test_metadictagger/")))
        metatag = factory.create_MetaDicTagger()
        metatag.prepare()
        return metatag


def assert_tags_pmc_4297_5600(test_suit, tags_4297, tags_5600):
    test_suit.assertIn("<Entity 399,426,intraventricular injection,DosageForm,MESH:D007276>", tags_4297)
    test_suit.assertIn("<Entity 636,646,injection,DosageForm,MESH:D007267>", tags_4297)

    test_suit.assertIn("<Entity 209,219,sparteine,Drug,DB06727>", tags_5600)
    test_suit.assertIn("<Entity 189,205,4-aminopyridine,Drug,DB06637>", tags_5600)
    test_suit.assertIn("<Entity 826,836,potassium,Excipient,DB14500>", tags_5600)


if __name__ == '__main__':
    unittest.main()
