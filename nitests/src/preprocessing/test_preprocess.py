import os
import unittest
import pytest
from narraint.pubtator.document import TaggedDocument

import nitests.config.config as config

from narraint.preprocessing import preprocess
from narraint.tools import proj_rel_path

class TestPreprocess(unittest.TestCase):
    output_file = proj_rel_path('nitests/tmp/output.pubtator')
    def test_333_files_DR_DF(self):
        #self.outputdir = config.make_test_tempdir()
        self.workdir = config.make_test_tempdir()
        args = [proj_rel_path('nitests/resources/infiles/333_abs.pubtator'),
                TestPreprocess.output_file,
                *f"-t DR DF --loglevel DEBUG -c DFTEST --composite --workdir {self.workdir}".split()
                ]
        preprocess.main(args)
        self.assertEqual(True, False)

    def test_output_integrity(self):

        TaggedDocument()

if __name__ == '__main__':
    unittest.main()
