import unittest

import rdflib

from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, Sentence, Predication
from narraint.extraction.export_predications import export_predications_as_tsv, export_predications_as_rdf
from nitests import util


class ExportPredicationsTest(unittest.TestCase):

    def setUp(self) -> None:
        session = SessionExtended.get()
        documents = [dict(id=1, collection="Test_Export", title="ABC", abstract=""),
                     dict(id=2, collection="Test_Export", title="DEF", abstract="")]
        Document.bulk_insert_values_into_table(session, documents)

        sentences = [dict(id=1, document_id=1, document_collection="Test_Export", text="Hello", md5hash="1"),
                     dict(id=2, document_id=1, document_collection="Test_Export", text="World", md5hash="2")]
        Sentence.bulk_insert_values_into_table(session, sentences)

        predications = [dict(id=11,
                             document_id=1, document_collection="Test_Export",
                             subject_id="A", subject_type="Drug", subject_str="ab",
                             predicate="treat", predicate_canonicalized="treats",
                             object_id="B", object_type="Disease", object_str="bc",
                             sentence_id=1, extraction_type="PathIE"),
                        dict(id=12,
                             document_id=1, document_collection="Test_Export",
                             subject_id="C", subject_type="Disease", subject_str="c a",
                             predicate="treat", predicate_canonicalized="treats",
                             object_id="B", object_type="Disease", object_str="b a",
                             sentence_id=1, extraction_type="PathIE"),
                        dict(id=13,
                             document_id=2, document_collection="Test_Export",
                             subject_id="A", subject_type="Disease", subject_str="a",
                             predicate="induce", predicate_canonicalized="induces",
                             object_id="B", object_type="Disease", object_str="b",
                             sentence_id=2, extraction_type="PathIE"),
                        dict(id=14,
                             document_id=2, document_collection="Test_Export",
                             subject_id="C", subject_type="Gene", subject_str="",
                             predicate="induce", predicate_canonicalized="induces",
                             object_id="D", object_type="Gene", object_str="",
                             sentence_id=2, extraction_type="PathIE"),
                        dict(id=15,
                             document_id=2, document_collection="Test_Export_Not",
                             subject_id="C", subject_type="Gene", subject_str="",
                             predicate="induce", predicate_canonicalized="induces",
                             object_id="D", object_type="Gene", object_str="",
                             sentence_id=2, extraction_type="PathIE")
                        ]
        Predication.bulk_insert_values_into_table(session, predications)

    def test_export_predications_as_tsv_without_metadata(self):
        output_file = util.tmp_rel_path("export_predications_without_metadata.tsv")
        export_predications_as_tsv(output_file, document_collection="Test_Export")

        tuples = set()
        with open(output_file, 'rt') as f:
            for line in f:
                tuples.add(tuple(line.strip().split('\t')))

        self.assertEqual(5, len(tuples))
        self.assertIn(('subject_id', 'relation', 'object_id'), tuples)
        self.assertIn(('A', 'treats', 'B'), tuples)
        self.assertIn(('C', 'treats', 'B'), tuples)
        self.assertIn(('A', 'induces', 'B'), tuples)
        self.assertIn(('C', 'induces', 'D'), tuples)

    def test_export_predications_as_tsv_with_metadata(self):
        output_file = util.tmp_rel_path("export_predications_with_metadata.tsv")
        export_predications_as_tsv(output_file, document_collection="Test_Export", export_metadata=True)

        tuples = set()
        with open(output_file, 'rt') as f:
            for line in f:
                tuples.add(tuple(line.strip().split('\t')))

        self.assertEqual(5, len(tuples))
        self.assertIn(("document_id", "document_collection",
                       "subject_id", "subject_type", "subject_str",
                       "predicate", "relation",
                       "object_id", "object_type", "object_str",
                       "sentence_id", "extraction_type"), tuples)
        self.assertIn(('1', 'Test_Export', 'A', 'Drug', 'ab', 'treat', 'treats', 'B', 'Disease', 'bc', '1', 'PathIE'),
                      tuples)
        self.assertIn(('1', 'Test_Export', 'C', 'Disease', 'c a', 'treat', 'treats', 'B', 'Disease', 'b a', '1', 'PathIE'),
                      tuples)
        self.assertIn(('2', 'Test_Export', 'A', 'Disease', 'a', 'induce', 'induces', 'B', 'Disease', 'b', '2', 'PathIE'),
                      tuples)
        self.assertIn(('2', 'Test_Export', 'C', 'Gene', '', 'induce', 'induces', 'D', 'Gene', '', '2', 'PathIE'),
                      tuples)

    def test_export_predications_as_rdf(self):
        output_file = util.tmp_rel_path("export_predications.rdf")
        export_predications_as_rdf(output_file, document_collection="Test_Export")

        g = rdflib.Graph()
        g.parse(output_file, format="turtle")
        tuples = set([(s.split('/')[-1], p.split('/')[-1], o.split('/')[-1]) for s, p, o in g])
        self.assertEqual(4, len(tuples))
        self.assertIn(('A', 'treats', 'B'), tuples)
        self.assertIn(('C', 'treats', 'B'), tuples)
        self.assertIn(('A', 'induces', 'B'), tuples)
        self.assertIn(('C', 'induces', 'D'), tuples)