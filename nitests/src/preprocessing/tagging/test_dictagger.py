import unittest
import os

from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.dosage import DosageFormTagger
from narraint.tools import proj_rel_path
from nitests.util import make_test_tempdir, create_test_kwargs, get_test_resource_filepath
import narraint.entity.enttypes as enttypes
import narraint.pubtator.document as doc


class TestDictagger(unittest.TestCase):
    def test_tag(self):
        out_file = proj_rel_path("nitests/tmp/MC1313813Tagged.txt")
        tagger = DosageFormTagger(**create_test_kwargs(get_test_resource_filepath("infiles/test_dictagger")))
        tagger.desc_by_term = {
            "protein": {"Desc1"},
            "proteins": {"Desc1"},
            "phorbol": {"Desc2", "Desc3"},
            "protein secretion": {"Desc4"}
        }
        tagger._tag(proj_rel_path("nitests/resources/infiles/test_dictagger/PMC1313813Untagged.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        document = doc.parse_tag_list(out_file)
        self.assertTrue(document)
        strings = [str(tag) for tag in document]
        self.assertIn("<Entity 0,8,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1103,1112,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1103,1112,proteins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1608,1626,protein secretion,DosageForm,Desc4>", strings)


if __name__ == '__main__':
    unittest.main()
