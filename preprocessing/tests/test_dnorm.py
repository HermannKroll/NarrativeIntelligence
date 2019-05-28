import os
import tempfile

from tagging.dnorm import DNorm
from tests.base import BaseTestCase


class Test(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.output = os.path.join(self.resource_dir, "dnorm/output.txt")
        self.result_expected = os.path.join(self.resource_dir, "dnorm/result.txt")

    def test_finalize(self):
        tmp = tempfile.mkdtemp()
        dnorm = DNorm(root_dir=tmp, log_dir=tmp, translation_dir=tmp)
        dnorm.result_file = os.path.join(tmp, "result.txt")
        dnorm.out_file = self.output
        dnorm.finalize()
        with open(dnorm.result_file) as f:
            content_result = f.read()
        with open(self.result_expected) as f:
            content_exptected = f.read()
        self.assertEqual(content_result, content_exptected)
