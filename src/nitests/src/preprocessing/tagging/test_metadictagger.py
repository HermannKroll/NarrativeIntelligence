import os
import unittest

import narrant.preprocessing.enttypes as et
import nitests.util as util
from narrant.preprocessing.tagging.metadictagger import PharmDictTagger
from narrant.pubtator.document import parse_tag_list, TaggedEntity
from narrant.pubtator.extract import read_tagged_documents


class TestMetadictagger(unittest.TestCase):
    ent_type_set = {et.DRUG, et.EXCIPIENT, et.DOSAGE_FORM, et.PLANT_FAMILY_GENUS}

    def test_init(self):
        metatag = TestMetadictagger.make_metatag()
        self.assertSetEqual(set(metatag._vocabs.keys()), TestMetadictagger.ent_type_set)
        self.assertIn("MESH:D007267", metatag._vocabs[et.DOSAGE_FORM]["injection"])
        self.assertIn("Agave", metatag._vocabs[et.PLANT_FAMILY_GENUS]["agave"])
        self.assertIn("CHEMBL412873", metatag._vocabs[et.DRUG]["sparteine"])

    def test_tag(self):
        in_1 = util.get_test_resource_filepath("infiles/test_metadictagger/4297.txt")
        out_1 = util.tmp_rel_path("out/4297.txt")
        os.makedirs(os.path.dirname(out_1), exist_ok=True)
        in_2 = util.get_test_resource_filepath("infiles/test_metadictagger/5600.txt")
        out_2 = util.tmp_rel_path("out/5600.txt")
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
        self.assertIn(TaggedEntity(None, 32926486, 716, 718, "eo", "Excipient", "CHEMBL1743219"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926486, 1234, 1236, "eo", "Excipient", "CHEMBL1743219"), out_file.tags)
        dftag = TaggedEntity(None, 32926486, 1366, 1369, "i-h", "DosageForm", "MESH:D000280")
        self.assertIn(dftag, out_file.tags)

    def test_custom_abbreviation_with_closing_space(self):
        in_file = util.get_test_resource_filepath("infiles/test_metadictagger/h2o2space_test.txt")
        metatag = TestMetadictagger.make_metatag()
        out_file = metatag.tag_doc([d for d in read_tagged_documents(in_file)][0])
        out_file.clean_tags()
        self.assertIn(TaggedEntity(None, 32926513, 61, 78, "hydrogen peroxide", "Excipient", "CHEMBL71595"),
                      out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 91, 108, "hydrogen peroxide", "Excipient", "CHEMBL71595"),
                      out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 110, 117, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 345, 352, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 462, 469, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 488, 495, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 573, 580, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 666, 673, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 949, 956, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)
        self.assertIn(TaggedEntity(None, 32926513, 1172, 1179, "h 2 o 2", "Excipient", "CHEMBL71595"), out_file.tags)

    @staticmethod
    def make_metatag():
        factory = PharmDictTagger(TestMetadictagger.ent_type_set,
                                  util.create_test_kwargs())
        metatag = factory.create_MetaDicTagger()
        metatag.prepare()
        return metatag


def assert_tags_pmc_4297_5600(test_suit, tags_4297, tags_5600):
    test_suit.assertIn("<Entity 400,426,intraventricular injection,DosageForm,MESH:D007276>", tags_4297)
    test_suit.assertIn("<Entity 637,646,injection,DosageForm,MESH:D007267>", tags_4297)

    test_suit.assertIn("<Entity 210,219,sparteine,Drug,CHEMBL412873>", tags_5600)
    test_suit.assertIn("<Entity 1311,1326,2-aminopyridine,Drug,CHEMBL21619>", tags_5600)
    test_suit.assertIn("<Entity 827,836,potassium,Excipient,CHEMBL1201290>", tags_5600)


if __name__ == '__main__':
    unittest.main()
