from unittest import TestCase

from narrant.config import PLANT_FAMILTY_DATABASE_FILE
from narrant.preprocessing.tagging.vocabularies import ExcipientVocabulary
from narraint.frontend.entity.autocompletion import AutocompletionUtil


class AutocompletionTestCase(TestCase):

    def setUp(self) -> None:
        self.autocompletion :AutocompletionUtil = AutocompletionUtil.instance()

    def test_autocompletion_drugs(self):
        metformin_gold = ["metformin"]
        metformin_ac_test = self.autocompletion.autocomplete("metfor")
        for test in metformin_gold:
            self.assertIn(test, metformin_ac_test)

        metformin_ac_test = self.autocompletion.autocomplete("metform")
        for test in metformin_gold:
            self.assertIn(test, metformin_ac_test)

        simvastatin_gold = ["simvastatin"]
        simvastatin_ac_test = self.autocompletion.autocomplete("simvasta")
        for test in simvastatin_gold:
            self.assertIn(test, simvastatin_ac_test)

    def test_autocompletion_diseases(self):
        diabetes_2_names = ['Diabetes Mellitus, Adult-Onset', 'Diabetes Mellitus, Ketosis-Resistant',
                            'Diabetes Mellitus, Maturity-Onset',
                            'Diabetes Mellitus, Non Insulin Dependent',
                            'Diabetes Mellitus, Non-Insulin-Dependent',
                            'Diabetes Mellitus, Noninsulin Dependent',
                            'Diabetes Mellitus, Noninsulin-Dependent',
                            'Diabetes Mellitus, Slow-Onset',
                            'Diabetes Mellitus, Stable',
                            'diabetes mellitus, Type II']
        diabetes_ac = self.autocompletion.autocomplete("diabetes")
        for test in diabetes_2_names:
            self.assertIn(test.lower(), diabetes_ac)

        neoplasms_terms = ['Neoplasms', 'Neoplasia', 'Neoplasm', 'Neoplasms']
        neoplas_ac = self.autocompletion.autocomplete("neoplas")
        for test in neoplasms_terms:
            self.assertIn(test.lower(), neoplas_ac)

    def test_autocompletion_genes(self):
        cyp3a4_names = ['CYP3A4', 'CYP3A', 'CYP3A3', 'CYP3A3', 'CYP3A4', 'CYP3A5']
        cyp3a4_ac = self.autocompletion.autocomplete('cyp3a')
        for test in cyp3a4_names:
            self.assertIn(test.lower(), cyp3a4_ac)

        self.assertIn('cytochrome P450 family 3 subfamily A member 4'.lower(),
                      self.autocompletion.autocomplete('cytochrome'))
        self.assertIn('mtor', self.autocompletion.autocomplete('mto'))
        self.assertIn('mechanistic target of rapamycin kinase',
                      self.autocompletion.autocomplete('mechanistic'))

    def test_mesh(self):
        self.assertIn('Cardiovascular Diseases'.lower(), self.autocompletion.autocomplete('cardiovascular di'))
        self.assertIn('Musculoskeletal Diseases'.lower(), self.autocompletion.autocomplete('musculoskeletal'))

    def test_excipients(self):
        excipient_names = ['ACETIC ACID', 'AMMONIO METHACRYLATE COPOLYMER TYPE A', 'HYDROCHLORIC ACID',
                           'HYDROXYETHYL CELLULOSE', 'POLYVINYL ALCOHOL']
        for en in excipient_names:
            self.assertIn(en.lower(), self.autocompletion.autocomplete(en.lower()[0:len(en) - 2]))

    def test_plant_families(self):
        plant_families_in_db = ['Atractylis', 'Cardamine', 'Chamaecytisus', 'Eurypelma', 'Juglans', 'Ophiopogon',
                                'Petroselinum', 'Plukenetia']
        for pf in plant_families_in_db:
            self.assertIn(pf.lower(), self.autocompletion.autocomplete(pf.lower()[0:len(pf) - 2]))



