import unittest

from narraint.cleaning.canonicalize_predicates import is_predicate_equal_to_vocab, transform_predicate


class CanonicalizePredicateTestCase(unittest.TestCase):

    def test_is_predicate_equal_to_vocab(self):
        self.assertTrue(is_predicate_equal_to_vocab("produce", "produce"))
        self.assertTrue(is_predicate_equal_to_vocab("produce", "*oduce"))
        self.assertTrue(is_predicate_equal_to_vocab("produce", "prod*"))
        self.assertTrue(is_predicate_equal_to_vocab("produce", "produc*"))
        self.assertTrue(is_predicate_equal_to_vocab("produce", "*duc*"))

    def test_transform_predicate(self):
        self.assertEqual("produce", transform_predicate("produce"))
        self.assertEqual("produce", transform_predicate("produced"))
        self.assertEqual("produce", transform_predicate("produces"))