import unittest

from narraint.atc.atc_tree import ATCTree


class TestATCTree(unittest.TestCase):

    def setUp(self) -> None:
        self.atc: ATCTree = ATCTree.instance()

    def test_drugs(self):
        biguanides_children = self.atc.get_drugs_for_atc_class('A10BA')
        self.assertIn('CHEMBL1431', biguanides_children)
        self.assertIn('CHEMBL170988', biguanides_children)
        self.assertIn('CHEMBL39736', biguanides_children)

        a10_children = self.atc.get_drugs_for_atc_class('A10')
        self.assertIn('CHEMBL1431', a10_children)
        self.assertIn('CHEMBL170988', a10_children)
        self.assertIn('CHEMBL39736', a10_children)

        a_children = self.atc.get_drugs_for_atc_class('A')
        self.assertIn('CHEMBL1431', a_children)
        self.assertIn('CHEMBL170988', a_children)
        self.assertIn('CHEMBL39736', a_children)

        self.assertGreater(len(a_children), len(a10_children))
        self.assertGreater(len(a10_children), len(biguanides_children))
        self.assertTrue(a10_children.issubset(a_children))
        self.assertTrue(biguanides_children.issubset(a10_children))
        self.assertTrue(biguanides_children.issubset(a_children))

        # maybe some strings are duplicated in the atc tree
        self.assertTrue(a_children.issubset(self.atc.get_drugs_for_atc_class_name('ALIMENTARY TRACT AND METABOLISM')))
        self.assertTrue(a10_children.issubset(self.atc.get_drugs_for_atc_class_name('DRUGS USED IN DIABETES')))
        self.assertTrue(biguanides_children.issubset(self.atc.get_drugs_for_atc_class_name('Biguanides')))