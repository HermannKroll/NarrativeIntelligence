import unittest
import filecmp

import pytest

from narraint.preprocessing.tagging.metadictagger import MetaDicTaggerFactory, MetaDicTagger
import narraint.entity.enttypes as et
import nitests.util as util
from narraint import tools
from narraint.pubtator.document import parse_tag_list


class TestMetadictagger(unittest.TestCase):
    ent_type_set = {et.DRUG, et.EXCIPIENT, et.DOSAGE_FORM, et.PLANT_FAMILY}

    def test_init(self):
        metatag = TestMetadictagger.make_metatag()
        self.assertSetEqual(set(metatag._vocabs.keys()), TestMetadictagger.ent_type_set)
        self.assertIn("DB00145", metatag._vocabs[et.EXCIPIENT]["glycine"])
        self.assertIn("MESH:D007267", metatag._vocabs[et.DOSAGE_FORM]["injection"])
        self.assertIn("Glycine", metatag._vocabs[et.PLANT_FAMILY]["glycine"])
        self.assertIn("DB06727", metatag._vocabs[et.DRUG]["sparteine"])

        # self.assertEqual(True, False)

    def test_tag(self):
        in_1 = util.get_test_resource_filepath("infiles/test_metadictagger/4297.txt")
        out_1 = tools.proj_rel_path("nitests/tmp/out/4297.txt")
        in_2 = util.get_test_resource_filepath("infiles/test_metadictagger/5600.txt")
        out_2 = tools.proj_rel_path("nitests/tmp/out/5600.txt")
        metatag = TestMetadictagger.make_metatag()
        metatag._tag(in_1, out_1)
        metatag._tag(in_2, out_2)
        tags_1 = [str(tag) for tag in parse_tag_list(out_1)]
        tags_2 = [str(tag) for tag in parse_tag_list(out_2)]

        self.assertIn("<Entity 399,426,intraventricular injection,DosageForm,MESH:D007276>", tags_1)
        self.assertIn("<Entity 636,646,injection,DosageForm,MESH:D007267>", tags_1)
        self.assertIn("<Entity 743,751,glycine,Excipient,DB00145>", tags_1)
        self.assertIn("<Entity 657,665,glycine,PlantFamily,Glycine>", tags_1)

        self.assertIn("<Entity 209,219,sparteine,Drug,DB06727", tags_2)
        self.assertIn("<Entity 189,205,4-aminopyridine,Drug,DB06637", tags_2)
        self.assertIn("<Entity 826,836,potassium,Excipient,DB14500", tags_2)

    @staticmethod
    def make_metatag():
        factory = MetaDicTaggerFactory(TestMetadictagger.ent_type_set,
                                       util.create_test_kwargs(
                                           util.get_test_resource_filepath("infiles/test_metadictagger/")))
        metatag = factory.create_MetaDicTagger()
        metatag.prepare()
        return metatag


if __name__ == '__main__':
    unittest.main()
