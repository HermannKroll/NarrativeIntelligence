import unittest

from narrant.backend.models import Document
from narrant.pubtator.document import TaggedDocument
from narrant.pubtator.extract import read_pubtator_documents
from narrant.pubtator.translation.patent import PatentConverter
from nitests.util import get_test_resource_filepath, tmp_rel_path


class TestPatentConverter(unittest.TestCase):

    def setUp(self) -> None:
        self.converter = PatentConverter()

    def test_convert_japan_patent(self):
        filename = get_test_resource_filepath("patents/patent_jp.txt")
        outfile = tmp_rel_path("patent_jp.pubtator")

        self.converter.convert(filename, outfile)
        doc = None
        with open(outfile, 'rt') as f:
            doc = TaggedDocument(f.read())

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = f.read()

        self.assertIn(doc.title, patent_content)
        self.assertIn(doc.abstract, patent_content)

    def test_convert_japan_patent_ignore_japanese_only_docs(self):
        filename = get_test_resource_filepath("patents/patent_jp_large.txt")
        outfile = tmp_rel_path("patent_jp_large.pubtator")
        self.converter.convert(filename, outfile)

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = Document.sanitize(f.read())

        doc_ids = set()
        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)
            self.assertIn(doc.title, patent_content)
            self.assertIn(doc.abstract, patent_content)
            # ignore country translation
            doc_ids.add(int(str(doc.id)[2:]))

        doc_ids_to_ignore = {2019537557, 2019537565, 2019537580}
        for did in doc_ids_to_ignore:
            self.assertNotIn(did, doc_ids)

    def test_convert_patent(self):
        filename = get_test_resource_filepath("patents/patent1.txt")
        outfile = tmp_rel_path("patent1.pubtator")

        self.converter.convert(filename, outfile)

        patent_content = None
        with open(filename, 'rt') as f:
            patent_content = f.read()

        for content in read_pubtator_documents(outfile):
            doc = TaggedDocument(content)
            self.assertIn(doc.title, patent_content)
            self.assertIn(doc.abstract, patent_content)
