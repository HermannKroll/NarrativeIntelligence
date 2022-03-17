import unittest

import nitests.util
from kgextractiontoolbox.document.extract import read_tagged_documents
from kgextractiontoolbox.document.load_document import document_bulk_load
from narrant.preprocessing import dictpreprocess
from nitests import util
from nitests.src.preprocessing.tagging.test_pharmdicttagger import assert_tags_pmc_4297_5600


class TestPreprocess(unittest.TestCase):

    def test_dictpreprocess_json_input(self):
        workdir = nitests.util.make_test_tempdir()
        args = [
            *f"-i {util.resource_rel_path('infiles/json_infiles')} -t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {workdir} -w 1 -y".split()
        ]
        dictpreprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(5297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {repr(t) for t in doc1}, {repr(t) for t in doc2})
        util.clear_database()

    def test_dictpreprocess_sinlge_worker_from_file(self):
        workdir = nitests.util.make_test_tempdir()
        path = util.resource_rel_path('infiles/test_metadictagger')
        args = [
            *f"-i {path} -t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {workdir} -w 1 -y".split()
        ]
        dictpreprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {repr(t) for t in doc1}, {repr(t) for t in doc2})
        util.clear_database()

    def test_dictpreprocess_sinlge_worker_from_database(self):
        workdir = nitests.util.make_test_tempdir()
        document_bulk_load(util.resource_rel_path('infiles/test_metadictagger'), collection="DBINSERTTAGGINGTEST")
        args = [*f"-t DR DF PF E -c DBINSERTTAGGINGTEST --loglevel DEBUG --workdir {workdir} -w 1 -y".split()]
        dictpreprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {repr(t) for t in doc1}, {repr(t) for t in doc2})
        util.clear_database()

    def test_dictpreprocess_dual_worker(self):
        workdir = nitests.util.make_test_tempdir()
        args = [
            *f"-i {util.resource_rel_path('infiles/test_metadictagger')} -t DR DF PF E -c PREPTEST --loglevel DEBUG --workdir {workdir} -w 2 -y".split()
        ]
        dictpreprocess.main(args)
        doc1, doc2 = util.get_tags_from_database(4297), util.get_tags_from_database(5600)
        assert_tags_pmc_4297_5600(self, {repr(t) for t in doc1}, {repr(t) for t in doc2})
        util.clear_database()

    def test_dictpreprocess_ignore_sections(self):
        in_file = util.get_test_resource_filepath("infiles/test_preprocess/fulltext_19128.json")
        workdir = nitests.util.make_test_tempdir()
        args = [
            *f"-i {in_file} -c PREPTEST --loglevel DEBUG --workdir {workdir} -w 2 -y".split()
        ]
        dictpreprocess.main(args)

        doc = list(read_tagged_documents(in_file))[0]
        title_section_len = len(doc.get_text_content(sections=False))
        doc_tags = util.get_tags_from_database(19128)
        for t in doc_tags:
            self.assertGreaterEqual(title_section_len, t.end)
        util.clear_database()

    def test_dictpreprocess_include_sections(self):
        in_file = util.get_test_resource_filepath("infiles/test_preprocess/fulltext_19128.json")
        workdir = nitests.util.make_test_tempdir()
        args = [
            *f"-i {in_file} -c PREPTEST --loglevel DEBUG --sections --workdir {workdir} -w 2 -y".split()
        ]
        dictpreprocess.main(args)

        doc = list(read_tagged_documents(in_file))[0]
        title_section_len = len(doc.get_text_content(sections=False))
        doc_len = len(doc.get_text_content(sections=True))
        doc_tags = util.get_tags_from_database(19128)
        tags_in_fulltext = []
        for t in doc_tags:
            if t.end > title_section_len:
                tags_in_fulltext.append(t)
            self.assertGreaterEqual(doc_len, t.end)

        self.assertLess(0, len(tags_in_fulltext))
        util.clear_database()


if __name__ == '__main__':
    unittest.main()
