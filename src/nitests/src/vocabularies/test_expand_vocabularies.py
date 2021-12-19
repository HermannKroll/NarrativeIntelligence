import unittest

from narrant.preprocessing.tagging.vocabulary import expand_vocabulary_term


class TestExpandVocabularyTerms(unittest.TestCase):

    def test_expand_vocabulary_term(self):
        terms = {"foo-bar-test", "bar foo test", "color", "neighbour", "party", "mars", "more"}
        check = terms | {"foo bar test", "foobartest", "bar-foo-test", "barfootest", "colour", "neighbor", "mar", "mor",
                         "colors", "colore", "marss"}
        exp_terms = {te for t in terms for te in expand_vocabulary_term(t)}
        self.assertTrue(check <= exp_terms)

    def test_expansion_rules(self):
        self.assertIn('families', list(expand_vocabulary_term("family")))
        self.assertIn('family', list(expand_vocabulary_term("families")))

        self.assertIn('tests', list(expand_vocabulary_term("test")))
        self.assertIn('test', list(expand_vocabulary_term("tests")))

        self.assertIn('test-case', list(expand_vocabulary_term("test-case")))
        self.assertIn('test-cases', list(expand_vocabulary_term("test-case")))

        self.assertIn('test case', list(expand_vocabulary_term("test-case")))
        self.assertIn('test cases', list(expand_vocabulary_term("test-case")))

        self.assertIn('testcase', list(expand_vocabulary_term("testcases")))
        self.assertIn('testcases', list(expand_vocabulary_term("testcase")))

        self.assertIn('test case', list(expand_vocabulary_term("test-cases")))
        self.assertIn('test cases', list(expand_vocabulary_term("test-cases")))

    def test_do_not_expand(self):
        term = "eudragit e"
        expanded_terms = list(expand_vocabulary_term(term))

        self.assertEqual(1, len(expanded_terms))
        self.assertIn(term, expanded_terms)