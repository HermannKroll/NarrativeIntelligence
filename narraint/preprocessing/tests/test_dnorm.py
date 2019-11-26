import os
import tempfile

from narraint.preprocessing.tagging import DNorm
from narraint.preprocessing.tests import BaseTestCase


class Test(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.dnorm_dir = os.path.join(self.resource_dir, "dnorm")
        self.output_1065332 = os.path.join(self.resource_dir, "dnorm/output_1065332.txt")
        self.output_1166567 = os.path.join(self.resource_dir, "dnorm/output_1166567.txt")
        self.result_expected_1065332 = os.path.join(self.resource_dir, "dnorm/result_1065332.txt")
        self.result_expected_1166567 = os.path.join(self.resource_dir, "dnorm/result_1166567.txt")

    def test_finalize_type_added(self):
        tmp = tempfile.mkdtemp()
        dnorm = DNorm(root_dir=tmp, log_dir=tmp, translation_dir=tmp)
        dnorm.result_file = os.path.join(tmp, "result.txt")
        dnorm.translation_dir = self.dnorm_dir
        dnorm.out_file = self.output_1065332
        dnorm.finalize()
        with open(dnorm.result_file) as f:
            content_result = f.read()
        with open(self.result_expected_1065332) as f:
            content_exptected = f.read()
        self.assertEqual(content_result, content_exptected)

    def test_finalize_index_adjusted(self):
        tmp = tempfile.mkdtemp()
        dnorm = DNorm(root_dir=tmp, log_dir=tmp, translation_dir=tmp)
        dnorm.result_file = os.path.join(tmp, "result.txt")
        dnorm.translation_dir = self.dnorm_dir
        dnorm.out_file = self.output_1166567
        dnorm.finalize()
        with open(dnorm.result_file) as f:
            content_result = f.read()
        with open(self.result_expected_1166567) as f:
            content_exptected = f.read()
        self.assertEqual(content_result, content_exptected)
