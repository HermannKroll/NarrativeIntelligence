import os
import unittest

import logging
import pytest

import nitests.config.config as config
import nitests.util

from narraint.preprocessing import preprocess
from narraint.tools import proj_rel_path
from narraint.pubtator.extract import read_tagged_documents
from nitests import util
from nitests.src.preprocessing.tagging.test_metadictagger import assert_tags_pmc_4297_5600


class TestPreprocess(unittest.TestCase):
    @pytest.mark.skip(reason="Not implemented yet")
    def test_single_file_DR(self):
        self.outputdir = nitests.util.make_test_tempdir()
        self.workdir = nitests.util.make_test_tempdir()
        print(self.outputdir)
        args = [proj_rel_path('nitests/resources/PMC1313813Untagged.txt'),
                os.path.join(self.outputdir, "output.txt"),
                *f"-t C D -c PREPTEST --loglevel DEBUG --workdir {self.workdir}".split()
                ]
        preprocess.main(args)
        self.assertEqual(True, False)

    #TODO: adjust tests to use database

    def test_metadictagger(self):
        self.output = os.path.join(nitests.util.make_test_tempdir(), "output.txt")
        logging.info(self.output)
        self.workdir = nitests.util.make_test_tempdir()
        args = [proj_rel_path('nitests/resources/infiles/test_metadictagger'),
                self.output,
                *f"-t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {self.workdir}".split()
                ]
        preprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {str(t) for t in doc1}, {str(t) for t in doc2})
        util.clear_database()


    #pytest.mark.skip(reason="export broke")
    def test_metadictagger_parallel(self):
        self.output = os.path.join(nitests.util.make_test_tempdir(), "output.txt")
        self.workdir = nitests.util.make_test_tempdir()
        args = [proj_rel_path('nitests/resources/infiles/test_metadictagger'),
                self.output,
                *f"-t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {self.workdir} -w 2".split()
                ]
        preprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {str(t) for t in doc1}, {str(t) for t in doc2})
        util.clear_database()

    


if __name__ == '__main__':
    unittest.main()
