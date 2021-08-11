import unittest

import narrant.preprocessing.vocab_dictpreprocess as vdp
import nitests
from narrant.pubtator.document import TaggedDocument

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

    def test_custom_abbreviations_and_synonyms(self):
        testfile = util.resource_rel_path('infiles/test_vocab_dictpreprocess/abbreviation_test_allowed.txt')
        self.tagfile_test(testfile)

    def test_vocab_expansion(self):
        self.tagfile_test(util.resource_rel_path('infiles/test_vocab_dictpreprocess/expansion_test.txt'))