from unittest import TestCase

from narraint.frontend.entity.autocompletion import AutocompletionUtil


class AutocompletionTestCase(TestCase):

    def setUp(self) -> None:
        self.autocompletion: AutocompletionUtil = AutocompletionUtil()

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

    def test_autocompletion_alternate_order(self):
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders("Diabetes Mellitus Adult")
        self.assertIn("Mellitus Diabetes Adult", alternate_orders)
        self.assertIn("Mellitus Adult Diabetes", alternate_orders)
        self.assertIn("Adult Mellitus Diabetes", alternate_orders)
        self.assertIn("Adult Diabetes Mellitus", alternate_orders)

        diabetes_2_names = ['Diabetes Mellitus',
                            'Diabetes Stable Mellitus',
                            'Diabetes Mellitus Stable'
                            ]

        diabetes_ac = self.autocompletion.autocomplete("diabetes")
        for test in diabetes_2_names:
            self.assertIn(test.lower(), diabetes_ac)

        alternate_orders = AutocompletionUtil.iterate_entity_name_orders("Absence Of Tibia")
        self.assertEqual(len(alternate_orders), 0)

        alternate_orders = AutocompletionUtil.iterate_entity_name_orders("Antihistamines For Systemic Use")
        self.assertEqual(len(alternate_orders), 0)

        alternate_orders = AutocompletionUtil.iterate_entity_name_orders("Epi Off Corneal Cross Linking")
        self.assertEqual(len(alternate_orders), 0)

        covid_ac = self.autocompletion.autocomplete("Post-acute")
        self.assertNotIn("Post-acute Sequelae Of Covid-19", covid_ac)

        covid_ac = self.autocompletion.autocomplete("Post-acute Covid-19")
        self.assertNotIn("Post-acute Covid-19 Sequelae Of", covid_ac)

    def test_autocompletion_alternate_order_conjunctions(self):
        term = "t1 t2 And t3 t4"
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders(term)
        self.assertEqual(len(alternate_orders), 8)
        self.assertIn("t1 t2 And t3 t4", alternate_orders)
        self.assertIn("t2 t1 And t3 t4", alternate_orders)
        self.assertIn("t1 t2 And t4 t3", alternate_orders)
        self.assertIn("t2 t1 And t4 t3", alternate_orders)
        self.assertIn("t3 t4 And t1 t2", alternate_orders)
        self.assertIn("t3 t4 And t2 t1", alternate_orders)
        self.assertIn("t4 t3 And t1 t2", alternate_orders)
        self.assertIn("t4 t3 And t2 t1", alternate_orders)

        term = "t1 t2 Or t3 t4"
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders(term)
        self.assertEqual(len(alternate_orders), 8)
        self.assertIn("t1 t2 Or t3 t4", alternate_orders)
        self.assertIn("t2 t1 Or t3 t4", alternate_orders)
        self.assertIn("t1 t2 Or t4 t3", alternate_orders)
        self.assertIn("t2 t1 Or t4 t3", alternate_orders)
        self.assertIn("t3 t4 Or t1 t2", alternate_orders)
        self.assertIn("t3 t4 Or t2 t1", alternate_orders)
        self.assertIn("t4 t3 Or t1 t2", alternate_orders)
        self.assertIn("t4 t3 Or t2 t1", alternate_orders)

        term = "t1 Or t2 Or t3"
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders(term)
        self.assertEqual(len(alternate_orders), 6)
        self.assertIn("t1 Or t2 Or t3", alternate_orders)
        self.assertIn("t1 Or t3 Or t2", alternate_orders)
        self.assertIn("t2 Or t1 Or t3", alternate_orders)
        self.assertIn("t2 Or t3 Or t1", alternate_orders)
        self.assertIn("t3 Or t2 Or t1", alternate_orders)
        self.assertIn("t3 Or t1 Or t2", alternate_orders)

        term = "t1 Or t2 And t3"
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders(term)
        self.assertEqual(len(alternate_orders), 6)
        self.assertIn("t1 Or t2 And t3", alternate_orders)
        self.assertIn("t1 Or t3 And t2", alternate_orders)
        self.assertIn("t2 Or t1 And t3", alternate_orders)
        self.assertIn("t2 Or t3 And t1", alternate_orders)
        self.assertIn("t3 Or t2 And t1", alternate_orders)
        self.assertIn("t3 Or t1 And t2", alternate_orders)

        term = "t1 Or t2 And t3 t4"
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders(term)
        self.assertEqual(len(alternate_orders), 12)
        self.assertIn("t1 Or t2 And t3 t4", alternate_orders)
        self.assertIn("t1 Or t2 And t4 t3", alternate_orders)
        self.assertIn("t1 Or t3 t4 And t2", alternate_orders)
        self.assertIn("t1 Or t4 t3 And t2", alternate_orders)
        self.assertIn("t2 Or t1 And t3 t4", alternate_orders)
        self.assertIn("t2 Or t1 And t4 t3", alternate_orders)
        self.assertIn("t2 Or t3 t4 And t1", alternate_orders)
        self.assertIn("t2 Or t4 t3 And t1", alternate_orders)
        self.assertIn("t3 t4 Or t2 And t1", alternate_orders)
        self.assertIn("t4 t3 Or t2 And t1", alternate_orders)
        self.assertIn("t3 t4 Or t1 And t2", alternate_orders)
        self.assertIn("t4 t3 Or t1 And t2", alternate_orders)

        term = "t1 Or t2 And t3 Or t4"
        alternate_orders = AutocompletionUtil.iterate_entity_name_orders(term)
        self.assertEqual(len(set(alternate_orders)), 24)
        # do not assert each element since the algorith scales factorial for single terms...

    def test_remove_redundant_terms(self):
        words = {'Complication', 'Complications', 'Complicationss'}
        self.assertEqual(1, len(AutocompletionUtil.remove_redundant_terms(words)))
        self.assertIn("Complication", AutocompletionUtil.remove_redundant_terms(words))

    def test_autocompletion_diseases(self):
        diabetes_2_names = ['Diabetes Mellitus, Adult Onset', 'Diabetes Mellitus, Ketosis Resistant',
                            'Diabetes Mellitus, Maturity Onset',
                            'Diabetes Mellitus, Non Insulin Dependent',
                            'Diabetes Mellitus, Non Insulin Dependent',
                            'Diabetes Mellitus, Noninsulin Dependent',
                            'Diabetes Mellitus, Noninsulin Dependent',
                            'Diabetes Mellitus, Slow Onset',
                            'Diabetes Mellitus, Stable',
                            'diabetes mellitus, Type II']
        diabetes_2_names = [AutocompletionUtil.remove_term_ending_comma(n) for n in diabetes_2_names]

        diabetes_ac = self.autocompletion.autocomplete("diabetes")
        for test in diabetes_2_names:
            self.assertIn(test.lower(), diabetes_ac)

        neoplasms_terms = ['Neoplasia', 'Neoplasm']
        neoplas_ac = self.autocompletion.autocomplete("neoplas")
        for test in neoplasms_terms:
            self.assertIn(test.lower(), neoplas_ac)

        # Neoplasm is contained so Neoplasms should not be suggested based on our "s" rule
        self.assertNotIn("Neoplasms", neoplas_ac)

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
        self.assertIn('Cardiovascular Disease'.lower(), self.autocompletion.autocomplete('cardiovascular di'))
        self.assertIn('Musculoskeletal Disease'.lower(), self.autocompletion.autocomplete('musculoskeletal'))
        # again "s" rule so only singular version
        self.assertNotIn('Cardiovascular Diseases'.lower(), self.autocompletion.autocomplete('cardiovascular di'))
        self.assertNotIn('Musculoskeletal Diseases'.lower(), self.autocompletion.autocomplete('musculoskeletal'))

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
