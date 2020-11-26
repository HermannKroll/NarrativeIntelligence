import os
import unittest
import pytest

import nitests.config.config as config

from narraint.preprocessing import preprocess
from narraint.tools import proj_rel_path

class TestPreprocess(unittest.TestCase):
    @pytest.mark.skip(reason="Not implemented yet")
    def test_single_file_DR(self):
        self.outputdir = config.make_test_tempdir()
        self.workdir = config.make_test_tempdir()
        args = [proj_rel_path('nitests/resources/infiles/PMC1313813Untagged.txt'),
                os.path.join(self.outputdir, "output.txt"),
                *f"-t DR C D DF -c PREPTEST --loglevel DEBUG --workdir {self.workdir}".split()
                ]
        preprocess.main(args)
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
