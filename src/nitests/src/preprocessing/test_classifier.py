import re
import unittest

from narrant.preprocessing.classifier import Classifyer
from narrant.pubtator.document import TaggedDocument
from nitests import util


class TestClassfier(unittest.TestCase):
    pet_rules = util.get_test_resource_filepath("classifier_rules/testrules.txt")

    def test_read_ruleset(self):
        rules = Classifyer.read_ruleset(TestClassfier.pet_rules)
        self.assertIn([re.compile(r"kitten\w*\b", re.IGNORECASE)], rules)
        self.assertIn([re.compile(r"dog\w*\b", re.IGNORECASE)], rules)
        self.assertIn([re.compile(r"hamster\b", re.IGNORECASE)], rules)
        self.assertIn([re.compile(r"animal\b", re.IGNORECASE), re.compile(r"house\b", re.IGNORECASE)], rules)

    def test_translate_rule(self):
        rule1 = 'volatile w/1 compound*'
        goal1 = r'volatile \w+ compound\w*\b'
        self.assertEqual(re.compile(goal1, re.IGNORECASE), Classifyer.compile_entry_to_regex(rule1))

        # apply regex
        re1_compiled = Classifyer.compile_entry_to_regex(rule1)
        test1 = 'volatile chinese compounds'
        self.assertTrue(re.match(re1_compiled, test1))
        test1_a = 'volatile chinese compoundsasdfdsafa'
        self.assertTrue(re.match(re1_compiled, test1_a))
        test1_b = 'volatile compound'
        self.assertFalse(re.match(re1_compiled, test1_b))

        rule2 = 'Traditional w/1 Medicine'
        goal2 = r'Traditional \w+ Medicine\b'
        self.assertEqual(re.compile(goal2, re.IGNORECASE), Classifyer.compile_entry_to_regex(rule2))

        # apply regex
        re2_compiled = Classifyer.compile_entry_to_regex(rule2)
        test2 = 'Traditional chinese Medicine'
        self.assertTrue(re.match(re2_compiled, test2))
        test2_a = 'Traditional Medicine'
        self.assertFalse(re.match(re2_compiled, test2_a))

        rule3 = rule1 + 'AND' + rule2
        self.assertIn(re.compile(goal1, re.IGNORECASE), Classifyer.compile_line_to_regex(rule3))
        self.assertIn(re.compile(goal2, re.IGNORECASE), Classifyer.compile_line_to_regex(rule3))

        rule3 = 'Traditional w/2 Medicine'
        goal3 = r'Traditional \w+ \w+ Medicine\b'
        self.assertEqual(re.compile(goal3, re.IGNORECASE), Classifyer.compile_entry_to_regex(rule3))

        rule4 = 'Traditional w/5 Medicine'
        goal4 = r'Traditional \w+ \w+ \w+ \w+ \w+ Medicine\b'
        self.assertEqual(re.compile(goal4, re.IGNORECASE), Classifyer.compile_entry_to_regex(rule4))

    def test_classify(self):
        classfier = Classifyer("pet", rule_path=TestClassfier.pet_rules)
        positive_docs = [
            TaggedDocument(title="some animals", abstract="Some people keep an animal in their house."),
            TaggedDocument(title="a cute hamster", abstract=""),
            TaggedDocument(title="two kittens for sale")
        ]
        negative_docs = [
            TaggedDocument(title="this has nothing to do with an animal"),
            TaggedDocument(title="this is about hamsters")
        ]
        for doc in positive_docs + negative_docs:
            classfier.classify_document(doc)

        for doc in positive_docs:
            self.assertIn('pet', doc.classification)
        for doc in negative_docs:
            self.assertNotIn('pet', doc.classification, msg=f"{doc}: false positive")
