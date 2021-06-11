import unittest

from narrant.preprocessing.enttypes import LAB_METHOD, METHOD
from narrant.preprocessing.tagging.vocabularies import MethodVocabulary, PlantFamilyVocabulary, expand_vocabulary_term


class VocabularyTest(unittest.TestCase):

    def test_read_method_classification(self):
        desc2class = MethodVocabulary.read_method_classification()
        self.assertEqual(LAB_METHOD, desc2class['MESH:D000069416'])
        self.assertEqual(LAB_METHOD, desc2class['MESH:D046169'])
        self.assertEqual(LAB_METHOD, desc2class['MESH:D015502'])

        self.assertEqual(METHOD, desc2class['MESH:D007089'])
        self.assertEqual(METHOD, desc2class['MESH:D005471'])
        self.assertEqual(METHOD, desc2class['MESH:D000071941'])

        self.assertEqual(None, desc2class['MESH:D061808'])
        self.assertEqual(None, desc2class['MESH:D003956'])

    def test_method_hand_crafted_rules(self):
        term2desc = {'spectrometry': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['spectrometry'])
        self.assertEqual(['D1'], enhanced_term2desc['spectrometric'])

        term2desc = {'spectrometric': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['spectrometry'])
        self.assertEqual(['D1'], enhanced_term2desc['spectrometric'])

        term2desc = {'spectrometric photo': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['spectrometry photo'])
        self.assertEqual(['D1'], enhanced_term2desc['spectrometric photo'])

        term2desc = {'spectrometry photo': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['spectrometry photo'])
        self.assertEqual(['D1'], enhanced_term2desc['spectrometric photo'])

        term2desc = {'test stain': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['test stain'])
        self.assertEqual(['D1'], enhanced_term2desc['test staining'])

        term2desc = {'stain': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['stain'])
        self.assertEqual(['D1'], enhanced_term2desc['staining'])

        term2desc = {'photostain': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['photostain'])
        self.assertEqual(['D1'], enhanced_term2desc['photostaining'])

        term2desc = {'staining and labeling': ['D1']}
        enhanced_term2desc = MethodVocabulary.enhance_methods_by_rules(term2desc)
        self.assertEqual(2, len(enhanced_term2desc))
        self.assertEqual(['D1'], enhanced_term2desc['staining and labeling'])
        self.assertEqual(['D1'], enhanced_term2desc['stain and labeling'])

    def test_read_plant_families(self):
        term2id = PlantFamilyVocabulary.read_plant_family_vocabulary(expand_terms=True)
        self.assertIn("Anamirta", term2id['anamirta'])
        self.assertIn("Anamirta", term2id['anamirtas'])
        self.assertIn("Anamirta", term2id['anamirtae'])
        self.assertIn("Anamirta", term2id['anamirtas'])
        self.assertIn("Anamirta", term2id['anamirtarum'])

        self.assertIn("Andira", term2id['andirae'])
        self.assertIn("Andira", term2id['andirae'])
        self.assertIn("Andira", term2id['andiras'])
        self.assertIn("Andira", term2id['andirarum'])

        self.assertIn("Artocarpus", term2id['artocarpus'])
        self.assertIn("Artocarpus", term2id['artocarpuum'])

        self.assertIn("Arum", term2id['arum'])
        self.assertIn("Arum", term2id['ari'])
        self.assertIn("Arum", term2id['ara'])
        self.assertIn("Arum", term2id['arorum'])
        self.assertIn("Arum", term2id['arums'])

    def test_expand_vocabulary_term(self):
        terms = {"foo-bar-test", "color", "neighbour", "party", "mars", "more"}
        check = terms | {"foo bar test", "foobartest", "colour", "neighbor", "mar", "mor", "colors", "colore", "marss"}
        exp_terms = {te for t in terms for te in expand_vocabulary_term(t)}
        self.assertTrue(check <= exp_terms)