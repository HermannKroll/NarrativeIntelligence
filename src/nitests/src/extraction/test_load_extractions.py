from unittest import TestCase

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narraint.extraction.loading.load_pathie_extractions import load_pathie_extractions
from narrant.backend.load_document import document_bulk_load
from nitests import util


class LoadExtractionsTestCase(TestCase):

    def setUp(self) -> None:
        documents_file = util.get_test_resource_filepath("extraction/documents_1.pubtator")
        document_bulk_load(documents_file, "Test_Load_PathIE_1")

    def test_load_pathie_extrations(self):
        pathie_file = util.get_test_resource_filepath("extraction/pathie_extractions_1.tsv")
        load_pathie_extractions(pathie_file, document_collection="Test_Load_PathIE_1", extraction_type="PathIE")

        session = SessionExtended.get()
        self.assertEqual(20, session.query(Predication).filter(Predication.document_collection == "Test_Load_PathIE_1").count())
