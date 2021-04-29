import os
import unittest

import logging
import pytest

import nitests.config.config as config
import nitests.util

from narraint.preprocessing import preprocess, dictpreprocess
from narraint.tools import proj_rel_path
from narraint.pubtator.extract import read_tagged_documents
from nitests import util
from nitests.src.preprocessing.tagging.test_metadictagger import assert_tags_pmc_4297_5600


class TestPreprocess(unittest.TestCase):

    def test_dictpreprocess_sinlge_worker(self):
        workdir = nitests.util.make_test_tempdir()
        args = [proj_rel_path('nitests/resources/infiles/test_metadictagger'),

                *f"-t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {workdir} -w 1 -y".split()
                ]
        dictpreprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {repr(t) for t in doc1}, {repr(t) for t in doc2})
        util.clear_database()

    def test_dictpreprocess_dual_worker(self):
        workdir = nitests.util.make_test_tempdir()
        args = [proj_rel_path('nitests/resources/infiles/test_metadictagger'),

                *f"-t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {workdir} -w 2 -y".split()
                ]
        dictpreprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {repr(t) for t in doc1}, {repr(t) for t in doc2})
        util.clear_database()
    


if __name__ == '__main__':
    unittest.main()
