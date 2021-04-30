import unittest
from nitests import util
from narrant.pubtator.extract import read_tagged_documents

from narrant.pubtator import sanitize


class TestSplit(unittest.TestCase):
    def test_filter_and_sanitize(self):
        target_ids = {33, 53, 54, 73, 75}
        in_file = util.get_test_resource_filepath("infiles/test_split/in.pubtator")
        out_file = util.tmp_rel_path("out/splitout.pubtator")
        sanitize.filter_and_sanitize(in_file, out_file, target_ids)
        out_ids = [td.id for td in read_tagged_documents(out_file)]
        self.assertSetEqual({33, 73, 75}, set(out_ids))
