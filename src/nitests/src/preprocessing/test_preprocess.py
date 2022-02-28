import unittest

import pytest

import nitests.util
from kgextractiontoolbox.document.load_document import document_bulk_load
from narrant.preprocessing import preprocess, dictpreprocess
from nitests import util
from nitests.src.preprocessing.tagging.test_metadictagger import assert_tags_pmc_4297_5600


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

    @pytest.mark.skip
    def test_gnormplus_preprocess(self):
        workdir = nitests.util.make_test_tempdir()
        args = [util.resource_rel_path('infiles/test_preprocess'),

                *f"--gnormplus -c PREPTEST --loglevel DEBUG".split()
                ]
        preprocess.main(args)
        print("after preprocess")
        doc = util.get_tags_from_database(12098649)
        print(doc)
        pass


if __name__ == '__main__':
    unittest.main()
