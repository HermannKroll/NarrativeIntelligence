import unittest

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.document.export import export
from kgextractiontoolbox.backend.models import Document, DocumentTranslation
from kgextractiontoolbox.document.document import TaggedDocument
from kgextractiontoolbox.document.extract import read_pubtator_documents
from narrant.pubtator.translation.doctranslation import run_document_translation
from narrant.pubtator.translation.patent import PatentConverter
from nitests.util import get_test_resource_filepath, tmp_rel_path


class TestPatentConverter(unittest.TestCase):

    def test_convert_japan_patent(self):
        filename = get_test_resource_filepath("patents/patent_jp.txt")
        outfile = tmp_rel_path("patent_jp.json")

        run_document_translation(filename, outfile, PatentConverter, collection="PatentTest")
        doc = None
        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = f.read()

        self.assertIn(doc.title, patent_content)
        self.assertIn(doc.abstract, patent_content)

        session = Session.get()
        titles = set([r[0] for r in session.query(Document.title).filter(Document.collection == "PatentTest")])
        abstracts = set([r[0] for r in session.query(Document.abstract).filter(Document.collection == "PatentTest")])
        trans_doc_ids = set([r[0] for r in session.query(DocumentTranslation.document_id)
                            .filter(DocumentTranslation.document_collection == "PatentTest")])

        self.assertIn(doc.title, titles)
        self.assertIn(doc.abstract, abstracts)
        self.assertIn(doc.id, trans_doc_ids)

    def test_convert_include_sanitized_texts(self):
        filename = get_test_resource_filepath("patents/patent_jp_large.txt")
        outfile = tmp_rel_path("patent_jp_large.json")
        run_document_translation(filename, outfile, PatentConverter, collection="PatentTest")

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = Document.sanitize(f.read())

        session = Session.get()
        titles = set([r[0] for r in session.query(Document.title).filter(Document.collection == "PatentTest")])
        abstracts = set([r[0] for r in session.query(Document.abstract).filter(Document.collection == "PatentTest")])
        trans_doc_ids = set([r[0] for r in session.query(DocumentTranslation.document_id)
                            .filter(DocumentTranslation.document_collection == "PatentTest")])

        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)
            self.assertIn(doc.title, patent_content)
            self.assertIn(doc.abstract, patent_content)

            self.assertIn(doc.title, titles)
            self.assertIn(doc.abstract, abstracts)
            self.assertIn(doc.id, trans_doc_ids)

        # are JP only documents ignored?
        doc_ids_to_ignore = {"JP19537557", "JP19537565", "JP2019537580"}
        source_ids = set([r[0] for r in session.query(DocumentTranslation.source_doc_id)
                         .filter(DocumentTranslation.document_collection == "PatentTest")])
        for doc_id in doc_ids_to_ignore:
            self.assertNotIn(doc_id, source_ids)

    def test_convert_patent(self):
        filename = get_test_resource_filepath("patents/patent1.txt")
        outfile = tmp_rel_path("patent1.json")

        run_document_translation(filename, outfile, PatentConverter, collection="PatentTest")

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = f.read()

        session = Session.get()
        titles = set([r[0] for r in session.query(Document.title).filter(Document.collection == "PatentTest")])
        abstracts = set([r[0] for r in session.query(Document.abstract).filter(Document.collection == "PatentTest")])
        trans_doc_ids = set([r[0] for r in session.query(DocumentTranslation.document_id)
                            .filter(DocumentTranslation.document_collection == "PatentTest")])

        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)
            self.assertIn(doc.title, patent_content)
            self.assertIn(doc.abstract, patent_content)

            self.assertIn(doc.title, titles)
            self.assertIn(doc.abstract, abstracts)
            self.assertIn(doc.id, trans_doc_ids)

    def test_export_translated_ids_pubtator(self):
        filename = get_test_resource_filepath("patents/patent1.txt")
        outfile = tmp_rel_path("patent1_trans.pubtator")

        run_document_translation(filename, outfile, PatentConverter, collection="PatentTest1")

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = f.read()
        patent_ids = set()
        for line in patent_content.split('\n'):
            patent_ids.add(line.split('|')[0])

        export(outfile, collection="PatentTest1", content=True, translate_document_ids=True, export_format="pubtator")

        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)
            self.assertIn(doc.id, patent_ids)
            self.assertIn(doc.title, patent_content)
            self.assertIn(doc.abstract, patent_content)

    def test_export_translated_ids_json(self):
        filename = get_test_resource_filepath("patents/patent1.txt")
        outfile = tmp_rel_path("patent1_trans.json")

        run_document_translation(filename, outfile, PatentConverter, collection="PatentTest2")

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = f.read()
        patent_ids = set()
        for line in patent_content.split('\n'):
            patent_ids.add(line.split('|')[0])

        export(outfile, collection="PatentTest2", content=True, translate_document_ids=True, export_format="json")

        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)
            self.assertIn(doc.id, patent_ids)
            self.assertIn(doc.title, patent_content)
            self.assertIn(doc.abstract, patent_content)
