import os
import tempfile

from preprocessing.tagging.base import get_pmcid_from_filename, get_exception_causing_file_from_log, finalize_dir, \
    merge_result_files
from preprocessing.tests.base import BaseTestCase


class Test(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.log_error = os.path.join(self.resource_dir, "gnorm_error.log")
        self.log_exception = os.path.join(self.resource_dir, "gnorm_exception.log")
        self.log_nothing = os.path.join(self.resource_dir, "gnorm_nothing.log")
        self.file_error = "/home/ruthmann/PubMedSnorkel/preprocessing/data/Simvastatin_22975/gnorm_in/PMC6003266.txt"
        self.file_exception = "/tmp/tmpmcxg6ers/translation/PMC3941952.txt"
        self.out_dir = os.path.join(self.resource_dir, "out_dir")
        self.batch_out_dir = os.path.join(self.resource_dir, "batch_out")
        self.expected_result_finalize_single = os.path.join(self.resource_dir, "result_finalize_single.txt")
        self.expected_result_finalize_batch = os.path.join(self.resource_dir, "result_finalize_batch.txt")
        self.expected_result_merge = os.path.join(self.resource_dir, "result_merge.txt")
        self.translation_dir = os.path.join(self.resource_dir, "translation")
        self.result_a = os.path.join(self.resource_dir, "result_a.txt")
        self.result_b = os.path.join(self.resource_dir, "result_b.txt")

    def test_get_pmcid_from_filename(self):
        self.assertEqual(get_pmcid_from_filename(self.file_exception), "PMC3941952")
        self.assertEqual(get_pmcid_from_filename("PMC3941952.txt"), "PMC3941952")
        self.assertEqual(get_pmcid_from_filename("PMC3941952"), "PMC3941952")

    def test_get_exception_causing_file_from_log_exception(self):
        fn = get_exception_causing_file_from_log(self.log_exception)
        self.assertEqual(fn, self.file_exception)

    def test_get_exception_causing_file_from_log_error(self):
        fn = get_exception_causing_file_from_log(self.log_error)
        self.assertEqual(fn, self.file_error)

    def test_get_exception_causing_file_from_log_nothing(self):
        fn = get_exception_causing_file_from_log(self.log_nothing)
        self.assertIsNone(fn)

    def test_finalize_dir_single(self):
        tmp_dir = tempfile.mkdtemp()
        result_file = os.path.join(tmp_dir, "tmp_result.txt")
        finalize_dir(self.out_dir, result_file)
        with open(self.expected_result_finalize_single) as f:
            content_expected = f.read()
        with open(result_file) as f:
            content_result = f.read()
        self.assertEqual(content_expected, content_result)

    def test_finalize_dir_batch(self):
        self.maxDiff = None
        tmp_dir = tempfile.mkdtemp()
        result_file = os.path.join(tmp_dir, "tmp_result.txt")
        finalize_dir(self.batch_out_dir, result_file, batch_mode=True)
        with open(self.expected_result_finalize_batch) as f:
            content_expected = f.read()
        with open(result_file) as f:
            content_result = f.read()
        self.assertEqual(content_expected, content_result)

    def test_merge_result_files(self):
        tmp_dir = tempfile.mkdtemp()
        output_file = os.path.join(tmp_dir, "tmp_result.txt")
        merge_result_files(self.translation_dir, output_file, self.result_a, self.result_b)
        with open(self.expected_result_merge) as f:
            content_expected = f.read()
        with open(output_file) as f:
            content_result = f.read()
        self.assertEqual(content_expected, content_result)
