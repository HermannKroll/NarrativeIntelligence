import re
import unittest

from narrant.preprocessing.classifier import Classifyer
from narrant.pubtator.document import TaggedDocument
from nitests import util


class TestClassfier(unittest.TestCase):
    pet_rules = util.get_test_resource_filepath("classifier_rules/testrules.txt")

    def test_read_ruleset(self):
        rules = Classifyer.read_ruleset(TestClassfier.pet_rules)
        self.assertIn([re.compile(r"kitten\w+\b", re.IGNORECASE)], rules)
        self.assertIn([re.compile(r"dog\w+\b", re.IGNORECASE)], rules)
        self.assertIn([re.compile(r"hamster\b", re.IGNORECASE)], rules)
        self.assertIn([re.compile(r"animal\b", re.IGNORECASE), re.compile(r"house\b", re.IGNORECASE)], rules)

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
