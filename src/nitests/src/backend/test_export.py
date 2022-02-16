import unittest

from narraint.backend.database import SessionExtended
from narrant.backend.export import export
from narrant.backend.load_document import document_bulk_load
from nitests import util


def setup_module(module):
    test_mapping = {"Drug": ("Drugtagger", "1.0"), "Disease": ("Diseasetagger", "1.0")}
    document_bulk_load(util.get_test_resource_filepath("infiles/test_export/in/"), "TEST_EXPORT", test_mapping)
    session = SessionExtended.get()
    pass


def teardown_module(module):
    util.clear_database()


class TestExport(unittest.TestCase):
    def test_export_pubtator(self):
        outfile = util.tmp_rel_path("export_out")
        testfile = util.get_test_resource_filepath("infiles/test_export/out/pubtator.txt")
        export(outfile, ["Drug", "Disease"], content=True, export_format="pubtator", collection="TEST_EXPORT")
        with open(outfile) as of, open(testfile) as tf:
            self.assertEqual(tf.read(), of.read())

    def test_export_json(self):
        outfile = util.tmp_rel_path("export_out")
        testfile = util.get_test_resource_filepath("infiles/test_export/out/json.txt")

        export(outfile, ["Drug", "Disease"], export_format="json", collection="TEST_EXPORT")
        with open(outfile) as of, open(testfile) as tf:
            self.assertEqual(tf.read(), of.read())
