import string
from unittest import TestCase

from narraint.frontend.entity.entityexplainer import EntityExplainer
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.config import PLANT_GENUS_DATABASE_FILE
from narrant.vocabularies.excipient_vocabulary import ExcipientVocabulary


class EntityExplanationTestCase(TestCase):

    def setUp(self) -> None:
        self.entity_explainer = EntityExplainer.instance()

    def test_chembl_entries(self):
        """
        Tests whether drugbank names and headings can be tagged correctly
        """
        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Metformin', truncate_at_k=1000)]
        self.assertIn('la-6023', terms)
        self.assertIn('metformin', terms)
        self.assertNotIn('metformin malt', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('LA-6023', truncate_at_k=1000)]
        self.assertIn('la-6023', terms)
        self.assertIn('metformin', terms)
        # Because Metformin should be included
        self.assertNotIn('metformin salt', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Simvastatin', truncate_at_k=1000)]
        self.assertIn('simvastatin', terms)
        self.assertIn('synvinolin', terms)
        self.assertIn('mk-0733', terms)
        self.assertIn('mk-733', terms)
        # Because Prefix Simvastatin should already be included
        self.assertNotIn('simvastatin hydroxy acid', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Amantadine', truncate_at_k=1000)]
        self.assertIn('amantadine', terms)
        self.assertIn('symadine', terms)
        self.assertIn('symmetrel', terms)

        terms = [t.lower() for t in self.entity_explainer.explain_entity_str('Avapritinib', truncate_at_k=1000)]
        self.assertIn('avapritinib', terms)

    def test_prefix_filter(self):
        prefixes = ['Diabetes',
                    'Diabetes Mellitus',
                    'Diabetes Mellitus Congenital',
                    'Diabetes Mellitus Congenital Autoimmune']
        test_prefixes = list(self.entity_explainer.get_prefixes('Diabetes Mellitus Congenital Autoimmune'))
        for p in prefixes:
            self.assertIn(p.lower(), test_prefixes)

        self.assertIn('diabetes', list(self.entity_explainer.get_prefixes('Diabetes')))

        test = ['Diabetes Mellitus',
                'Diabetes Meitus',
                'Diabetes Mellitus, Congenital Autoimmune']

        f_test = self.entity_explainer.filter_names_for_prefix_duplicates(test)
        self.assertIn('Diabetes Mellitus', f_test)
        self.assertIn('Diabetes Meitus', f_test)
        self.assertNotIn('Diabetes Mellitus, Congenital Autoimmune', f_test)

        test = ['Diabetes Mellitus',
                'Diabetes Mellitus Congenital Autoimmune']

        f_test = self.entity_explainer.filter_names_for_prefix_duplicates(test)
        self.assertIn('Diabetes Mellitus', f_test)
        self.assertNotIn('Diabetes Mellitus Congenital Autoimmune', f_test)

        test = ['Ace',
                'Acetabulum']

        f_test = self.entity_explainer.filter_names_for_prefix_duplicates(test)
        self.assertIn('Ace', f_test)
        self.assertIn('Acetabulum', f_test)

    def test_mesh_entries(self):
        """
        Tests whether MeSH entries can be tagged correctly
            :return:
        """
        diabetes_2_names = ['Diabetes Mellitus',
                            'NIDDM',
                            'Noninsulin Dependent Diabetes Mellitus']

        terms = self.entity_explainer.explain_entity_str('Diabetes Mellitus', truncate_at_k=1000)
        for dn in diabetes_2_names:
            self.assertIn(dn, terms)

        # These names should be not included because Diabetes Mellitus is a prefix of them
        diabetes_already_included_names = ['Diabetes Mellitus, Adult-Onset',
                                           'Diabetes Mellitus, Ketosis-Resistant',
                                           'Diabetes Mellitus, Maturity-Onset',
                                           'Diabetes Mellitus, Non Insulin Dependent',
                                           'Diabetes Mellitus, Non-Insulin-Dependent',
                                           'Diabetes Mellitus, Noninsulin Dependent',
                                           'Diabetes Mellitus, Noninsulin-Dependent',
                                           'Diabetes Mellitus, Slow-Onset',
                                           'Diabetes Mellitus, Stable',
                                           'Diabetes Mellitus, Type II', ]
        for dn in diabetes_already_included_names:
            self.assertNotIn(dn, terms)

        neoplasms_terms = ['Neoplasms',
                           'Benign Neoplasms',
                           'Cancer',
                           'Malignancy',
                           'Malignant Neoplasms',
                           'Neoplasia',
                           'Neoplasm',
                           'Tumors']

        terms = self.entity_explainer.explain_entity_str('Cancer', truncate_at_k=10000)
        for nt in neoplasms_terms:
            self.assertIn(nt, terms)

        # Neoplasm is a prefix, thus it should not be included
        self.assertNotIn('Neoplasms, Benign', terms)

    def test_mesh_supplement_entries(self):
        self.assertIn('Absence of Tibia', [t for t in self.entity_explainer.explain_entity_str('Absence of Tibia')])

    def test_plant_families(self):
        """
        Tests whether plant family names can be tagged correctly
        """
        plant_families_in_db = []
        with open(PLANT_GENUS_DATABASE_FILE, 'rt') as f:
            plant_families_in_db = [line.strip() for line in f]

        for pf in plant_families_in_db:
            self.assertIn(pf.lower(),
                          [t.lower() for t in self.entity_explainer.explain_entity_str(pf, truncate_at_k=10000)])

    def test_excipient_names(self):
        """
        Tests whether excipient names can be tagged correctly
        """
        excipient_names = [n for n in ExcipientVocabulary.read_excipients_names(expand_terms=False)]
        trans_map = {p: '' for p in string.punctuation}
        translator = str.maketrans(trans_map)
        for en in excipient_names:
            if en.strip() and len(en.strip()) > 1:
                try:
                    # ignore punctuation and lower/upper case
                    self.assertIn(en.translate(translator).lower(),
                                  [t.translate(translator).lower() for t in
                                   self.entity_explainer.explain_entity_str(en, truncate_at_k=10000)])
                except AssertionError:
                    # Try prefixes - Maybe a shorter version is included
                    # if a prefix is included everything is fine (one synonym was a prefix of the long version)
                    result = list([t.translate(translator).lower() for t in
                                   self.entity_explainer.explain_entity_str(en, truncate_at_k=10000)])
                    found = False
                    for pref in self.entity_explainer.get_prefixes(en):
                        if pref in result:
                            found = True
                            break
                    self.assertTrue(found)

    def test_gene_names(self):
        cyp3a4_names = ['CYP3A4', 'HLP', 'CP33', 'CP34', 'CYP3A', 'NF-25', 'CYP3A3',
                        'P450C3', 'CYPIIIA3', 'CYPIIIA4', 'P450PCN1']
        terms = [t for t in self.entity_explainer.explain_entity_str('CYP3A4', truncate_at_k=1000)]
        for n in cyp3a4_names:
            self.assertIn(n, terms)

        mtor_names = ['MTOR', 'mechanistic target of rapamycin', 'SKS', 'FRAP', 'FRAP1', 'FRAP2', 'RAFT1', 'RAPT1']
        terms = [t for t in self.entity_explainer.explain_entity_str('MTOR', truncate_at_k=1000)]
        for n in mtor_names:
            self.assertIn(n, terms)

        cyp3a5_names = ['CYP3A5', 'cytochrome P450 family 3 subfamily A member 5',
                        'CP35', 'CYPIIIA5', 'P450PCN3', 'PCN3']
        terms = [t for t in self.entity_explainer.explain_entity_str('cyp3a5', truncate_at_k=1000)]
        for n in cyp3a5_names:
            self.assertIn(n, terms)

    def test_nano_particle(self):
        names = ['Nanoparticles']
        for n1 in names:
            terms = [t for t in self.entity_explainer.explain_entity_str(n1, truncate_at_k=1000)]
            for n2 in names:
                self.assertIn(n2, terms)

    def test_explain_concept_prefix_filter(self):
        headings = self.entity_explainer.explain_entity_str("Diabetes", truncate_at_k=10000)
        self.assertIn("Diabetes Mellitus", headings)
        self.assertNotIn("Diabetes Mellitus Type 1", headings)
        self.assertNotIn("Diabetes Mellitus Type 2", headings)

        headings = self.entity_explainer.explain_entity_str("Covid 19", truncate_at_k=10000)
        self.assertIn("COVID-19", headings)
        self.assertNotIn("COVID-19 Drug Treatment", headings)
        self.assertNotIn("COVID-19 Testing", headings)

    def test_explain_concept_to_large(self):
        headings = self.entity_explainer.explain_entity_str("Disease")
        self.assertEqual(1, len(headings))
