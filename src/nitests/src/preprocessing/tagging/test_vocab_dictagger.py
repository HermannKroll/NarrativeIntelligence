import unittest

import kgextractiontoolbox.entitylinking.vocab_entity_linking as vdp
import nitests
from kgextractiontoolbox.document.document import TaggedDocument
from nitests import util


class TestVocabDictagger(unittest.TestCase):
    def tagfile_test(self, testfile):
        workdir = nitests.util.make_test_tempdir()
        args = [testfile,

                *f"-c PREPTEST --loglevel DEBUG -v {util.resource_rel_path('vocabs/test_vocab.tsv')} --workdir {workdir} -w 1 -y".split()
                ]
        vdp.main(args)
        tags = set(util.get_tags_from_database())
        test_tags = set(TaggedDocument(testfile).tags)
        self.assertSetEqual(tags, test_tags)
        util.clear_database()