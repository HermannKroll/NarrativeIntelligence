import unittest
import os

from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.dosage import DosageFormTagger
from narraint.tools import proj_rel_path
from nitests.config.config import make_test_tempdir
import narraint.entity.enttypes as enttypes
from narraint.pubtator.document import TaggedDocument
import narraint.preprocessing.config as cnf


class TestDictagger(unittest.TestCase):
    def test_tag(self):
        config = cnf.Config(PREPROCESS_CONFIG)
        out_file = proj_rel_path("nitests/tmp/MC1313813Tagged.txt")
        tagger = DosageFormTagger(config=config, log_dir=proj_rel_path("nitests/tmp/"), root_dir=make_test_tempdir())
        #tagger.desc_by_term = {"Desc1": {"proteins", "protein"}, "Desc2": {"phorbol",}}
        tagger.desc_by_term = {"protein": {"Desc1"}, "proteins": {"Desc1"}, "phorbol": {"Desc2", "Desc3"}}
        tagger._tag(proj_rel_path("nitests/resources/infiles/PMC1313813Untagged.txt"),
                    out_file)
        self.assertTrue(os.path.isfile(out_file))
        document = TaggedDocument(out_file)
        for tag in document.tags:
            print(tag)
        pass
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
