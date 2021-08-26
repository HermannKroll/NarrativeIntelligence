from unittest import TestCase

from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narraint.extraction.loading.load_openie_extractions import load_openie_tuples, OpenIEEntityFilterMode
from narrant.backend.load_document import document_bulk_load
from nitests import util


class LoadExtractionsTestCase(TestCase):

    def setUp(self) -> None:
        documents_file = util.get_test_resource_filepath("extraction/documents_1.pubtator")
        document_bulk_load(documents_file, "Test_Load_OpenIE_1")

    def test_load_openie_extrations(self):
        session = SessionExtended.get()
        session.execute(delete(Predication).where(Predication.document_collection == 'Test_Load_OpenIE_1'))
        session.commit()

        openie_file = util.get_test_resource_filepath("extraction/openie_extractions_1.tsv")
        load_openie_tuples(openie_file, document_collection="Test_Load_OpenIE_1",
                           entity_filter=OpenIEEntityFilterMode.NO_ENTITY_FILTER)

        self.assertEqual(8, session.query(Predication).filter(
            Predication.document_collection == "Test_Load_OpenIE_1").count())
        tuples = set()
        for q in Predication.iterate_predications_joined_sentences(session, document_collection="Test_Load_OpenIE_1"):
            tuples.add((q.Predication.document_id, q.Predication.document_collection,
                        q.Predication.subject_id, q.Predication.subject_type, q.Predication.subject_str,
                        q.Predication.predicate, q.Predication.relation,
                        q.Predication.object_id, q.Predication.object_type, q.Predication.object_str,
                        q.Predication.extraction_type, q.Sentence.text))

        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'tacrolimus', 'Unknown', 'tacrolimus',
                       'induce', None,
                       'onset scleroderma crisis', 'Unknown', 'onset scleroderma crisis', 'OpenIE',
                       'Late - onset scleroderma renal crisis induced by tacrolimus and prednisolone : a case report .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'tacrolimus', 'Unknown', 'tacrolimus',
                       'induce', None,
                       'onset scleroderma renal crisis', 'Unknown', 'onset scleroderma renal crisis', 'OpenIE',
                       'Late - onset scleroderma renal crisis induced by tacrolimus and prednisolone : a case report .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'major risk factor', 'Unknown', 'major risk factor',
                       'recognize', None,
                       'moderate', 'Unknown', 'moderate', 'OpenIE',
                       'Moderate to high dose corticosteroid use is recognized as a major risk factor for SRC .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'risk factor for src', 'Unknown', 'risk factor for src',
                       'recognize', None,
                       'moderate', 'Unknown', 'moderate', 'OpenIE',
                       'Moderate to high dose corticosteroid use is recognized as a major risk factor for SRC .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'major risk factor for src', 'Unknown', 'major risk factor for src',
                       'recognize', None,
                       'moderate', 'Unknown', 'moderate', 'OpenIE',
                       'Moderate to high dose corticosteroid use is recognized as a major risk factor for SRC .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'risk factor', 'Unknown', 'risk factor',
                       'recognize', None,
                       'moderate', 'Unknown', 'moderate', 'OpenIE',
                       'Moderate to high dose corticosteroid use is recognized as a major risk factor for SRC .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'cyclosporine patients', 'Unknown', 'cyclosporine patients',
                       'precipitate', None,
                       'have reports', 'Unknown', 'have reports', 'OpenIE',
                       'Furthermore , there have been reports of thrombotic microangiopathy precipitated by cyclosporine in patients with SSc .'),
                      tuples)
        self.assertIn((22836123, 'Test_Load_OpenIE_1',
                       'cyclosporine patients ssc', 'Unknown', 'cyclosporine patients ssc',
                       'precipitate', None,
                       'have reports', 'Unknown', 'have reports', 'OpenIE',
                       'Furthermore , there have been reports of thrombotic microangiopathy precipitated by cyclosporine in patients with SSc .'),
                      tuples)

