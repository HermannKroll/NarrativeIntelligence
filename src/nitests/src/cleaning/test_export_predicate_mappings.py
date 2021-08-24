import unittest

from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, Sentence, Predication
from narraint.cleaning.export_predicate_mappings import export_predicate_mapping
from nitests import util


class PredicateMappingExportTest(unittest.TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()
        documents = [dict(id=1, collection="Test_Export_Mappings", title="ABC", abstract=""),
                     dict(id=2, collection="Test_Export_Mappings", title="DEF", abstract="")]
        Document.bulk_insert_values_into_table(session, documents)

        sentences = [dict(id=1, document_id=1, document_collection="Test_Export_Mappings", text="Hello", md5hash="1"),
                     dict(id=2, document_id=1, document_collection="Test_Export_Mappings", text="World", md5hash="2")]
        Sentence.bulk_insert_values_into_table(session, sentences)

        predications = [dict(id=1,
                             document_id=1, document_collection="Test_Export_Mappings",
                             subject_id="A", subject_type="Drug", subject_str="",
                             predicate="treats", predicate_canonicalized="treats",
                             object_id="B", object_type="Disease", object_str="",
                             sentence_id=1, extraction_type="PathIE"),
                        dict(id=2,
                             document_id=1, document_collection="Test_Export_Mappings",
                             subject_id="A", subject_type="Disease", subject_str="",
                             predicate="treats", predicate_canonicalized="treats",
                             object_id="B", object_type="Disease", object_str="",
                             sentence_id=1, extraction_type="PathIE"),
                        dict(id=3,
                             document_id=2, document_collection="Test_Export_Mappings",
                             subject_id="A", subject_type="Disease", subject_str="",
                             predicate="induces", predicate_canonicalized="induces",
                             object_id="B", object_type="Disease", object_str="",
                             sentence_id=2, extraction_type="PathIE"),
                        dict(id=4,
                             document_id=2, document_collection="Test_Export_Mappings",
                             subject_id="A", subject_type="Gene", subject_str="",
                             predicate="induces", predicate_canonicalized="induces",
                             object_id="B", object_type="Gene", object_str="",
                             sentence_id=2, extraction_type="PathIE"),
                        dict(id=5,
                             document_id=2, document_collection="Test_Export_Mappings",
                             subject_id="A", subject_type="Gene", subject_str="",
                             predicate="therapy", predicate_canonicalized="therapy",
                             object_id="B", object_type="Gene", object_str="",
                             sentence_id=2, extraction_type="PathIE"),
                        dict(id=6,
                             document_id=2, document_collection="Test_Export_Mappings",
                             subject_id="A", subject_type="Gene", subject_str="",
                             predicate="test",
                             object_id="B", object_type="Gene", object_str="",
                             sentence_id=2, extraction_type="PathIE")
                        ]
        Predication.bulk_insert_values_into_table(session, predications)

    def test_export_predicate_mappings(self):
        output_file = util.tmp_rel_path("predicate_mappings.tsv")
        export_predicate_mapping(output_file, "Test_Export_Mappings")
        output_results = set()
        with open(output_file, 'rt') as f:
            for line in f:
                output_results.add(tuple(line.strip().split('\t')))

        self.assertIn(('predicate', 'count', 'relation'), output_results)
        self.assertIn(("treats", "2", "treats"), output_results)
        self.assertIn(("induces", "2", "induces"), output_results)
        self.assertIn(("therapy", "1", "therapy"), output_results)
        self.assertIn(("test", "1", "None"), output_results)
