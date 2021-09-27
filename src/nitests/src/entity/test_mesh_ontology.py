from unittest import TestCase

from narrant.entity.meshontology import MeSHOntology
from narrant.preprocessing.enttypes import DISEASE, METHOD, DOSAGE_FORM


class MeSHOntologyTestCase(TestCase):

    def setUp(self) -> None:
        self.ontology: MeSHOntology = MeSHOntology.instance()

    def test_tree_number_to_entity_type(self):
        self.assertIn(DISEASE, MeSHOntology.tree_number_to_entity_type('C01.2351.23'))
        self.assertIn(DISEASE, MeSHOntology.tree_number_to_entity_type('C01.23'))
        self.assertIn(DISEASE, MeSHOntology.tree_number_to_entity_type('C03.23'))
        self.assertIn(DISEASE, MeSHOntology.tree_number_to_entity_type('F03.2351.23'))
        self.assertIn(DISEASE, MeSHOntology.tree_number_to_entity_type('F03.23.1234'))
        self.assertIn(DISEASE, MeSHOntology.tree_number_to_entity_type('F03.23'))

        self.assertIn(METHOD, MeSHOntology.tree_number_to_entity_type('E01.2351.23'))
        self.assertIn(METHOD, MeSHOntology.tree_number_to_entity_type('E01.23'))
        self.assertIn(METHOD, MeSHOntology.tree_number_to_entity_type('E03.23'))
        self.assertIn(METHOD, MeSHOntology.tree_number_to_entity_type('E03.2351.23'))
        self.assertIn(METHOD, MeSHOntology.tree_number_to_entity_type('E03.23.1234'))
        self.assertIn(METHOD, MeSHOntology.tree_number_to_entity_type('E03.23'))

        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type('E01.2351.23'))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type('E01.23'))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type('E03.23'))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type('E03.2351.23'))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type('E03.23.1234'))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type('E03.23'))

        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("J01.637.512.600"))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("J01.637.512.600.1234"))

        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("J01.637.512.850"))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("J01.637.512.850.534"))

        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("J01.637.512.925"))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("J01.637.512.925.1324"))

        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("D26.255"))
        self.assertIn(DOSAGE_FORM, MeSHOntology.tree_number_to_entity_type("D26.255.1324"))

        self.assertRaises(KeyError, MeSHOntology.tree_number_to_entity_type, 'Z...')
        self.assertRaises(KeyError, MeSHOntology.tree_number_to_entity_type, 'M...')

    def test_get_tree_numbers_for_descriptor(self):
        tree_numbers = ['E02.319.300']
        self.assertEqual(1, len(self.ontology.get_tree_numbers_for_descriptor('D016503')))
        for tn in self.ontology.get_tree_numbers_for_descriptor('D016503'):
            self.assertIn(tn, tree_numbers)

        tree_numbers = ['D26.255.260.575', 'E02.319.300.380.575', 'J01.637.512.600.575']
        self.assertEqual(3, len(self.ontology.get_tree_numbers_for_descriptor('D053769')))
        for tn in self.ontology.get_tree_numbers_for_descriptor('D053769'):
            self.assertIn(tn, tree_numbers)

        tree_numbers = ['E05.290.500', 'H01.158.703.007.338.500', 'H01.181.466.338.500']
        self.assertEqual(3, len(self.ontology.get_tree_numbers_for_descriptor('D015195')))
        for tn in self.ontology.get_tree_numbers_for_descriptor('D015195'):
            self.assertIn(tn, tree_numbers)

    def test_get_tree_numbers_with_entity_type_for_descriptor(self):
        tree_numbers = ['D26.255.260.575', 'E02.319.300.380.575', 'J01.637.512.600.575']
        self.assertEqual(3, len(self.ontology.get_tree_numbers_with_entity_type_for_descriptor('D053769')))
        for tn in self.ontology.get_tree_numbers_with_entity_type_for_descriptor('D053769'):
            self.assertIn(tn, tree_numbers)

        tree_numbers = ['E05.290.500']
        self.assertEqual(1, len(self.ontology.get_tree_numbers_with_entity_type_for_descriptor('D015195')))
        for tn in self.ontology.get_tree_numbers_with_entity_type_for_descriptor('D015195'):
            self.assertIn(tn, tree_numbers)
