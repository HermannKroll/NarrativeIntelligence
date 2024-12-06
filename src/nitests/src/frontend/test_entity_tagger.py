from unittest import TestCase

from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.config import PLANT_GENUS_DATABASE_FILE
from narrant.vocabularies.excipient_vocabulary import ExcipientVocabulary


class EntityTaggerTestCase(TestCase):

    def setUp(self) -> None:
        self.entity_tagger = EntityTagger()

    def test_drugs_without_e(self):
        self.assertEqual(len(self.entity_tagger.tag_entity('codein', expand_search_by_prefix=False)),
                         len(self.entity_tagger.tag_entity('codeine', expand_search_by_prefix=False)))

        self.assertEqual(len(self.entity_tagger.tag_entity('Codein', expand_search_by_prefix=False)),
                         len(self.entity_tagger.tag_entity('Codeine', expand_search_by_prefix=False)))

        for ent in self.entity_tagger.tag_entity('codeine', expand_search_by_prefix=True):
            self.assertIn(ent, self.entity_tagger.tag_entity('codein', expand_search_by_prefix=True))

        for ent in self.entity_tagger.tag_entity('Codeine', expand_search_by_prefix=True):
            self.assertIn(ent, self.entity_tagger.tag_entity('Codein', expand_search_by_prefix=True))

        self.assertEqual(len(self.entity_tagger.tag_entity('Furosemid', expand_search_by_prefix=False)),
                         len(self.entity_tagger.tag_entity('Furosemide', expand_search_by_prefix=False)))

        for ent in self.entity_tagger.tag_entity('Furosemide', expand_search_by_prefix=True):
            self.assertIn(ent, self.entity_tagger.tag_entity('Furosemid', expand_search_by_prefix=True))

    def test_chembl_entries(self):
        """
        Tests whether drugbank names and headings can be tagged correctly
        """
        metformin_tags = self.entity_tagger.tag_entity('metformin', expand_search_by_prefix=False)
        valid_metformin_ids = {'CHEMBL1431'}
        self.assertEqual(1, len(metformin_tags))
        for t in metformin_tags:
            self.assertIn(t.entity_id, valid_metformin_ids)
        self.assertIn('CHEMBL1431', [t.entity_id for t in self.entity_tagger.tag_entity('LA-6023')])
        self.assertIn('CHEMBL1431', [t.entity_id for t in self.entity_tagger.tag_entity('Metformin')])

        simvastatin_tags = self.entity_tagger.tag_entity('simvastatin', expand_search_by_prefix=False)
        valid_simvastatin_ids = {'CHEMBL1064'}
        self.assertEqual(1, len(simvastatin_tags))
        for t in simvastatin_tags:
            self.assertIn(t.entity_id, valid_simvastatin_ids)

        self.assertEqual('CHEMBL1064', next(iter(self.entity_tagger.tag_entity('SYNVINOLIN'))).entity_id)
        self.assertIn('CHEMBL1064',
                      list([e.entity_id for e in self.entity_tagger.tag_entity('Simvastatin hydroxy acid')]))
        self.assertEqual('CHEMBL1064', next(iter(self.entity_tagger.tag_entity('MK-0733'))).entity_id)

        acetarsol_tags = self.entity_tagger.tag_entity('acetarsol', expand_search_by_prefix=False)
        valid_acetarsol_ids = {'CHEMBL1330792'}
        for t in acetarsol_tags:
            self.assertIn(t.entity_id, valid_acetarsol_ids)

        valid_amantadine_ids = {'CHEMBL660'}
        for t in self.entity_tagger.tag_entity('Amantadine', expand_search_by_prefix=False):
            self.assertIn(t.entity_id, valid_amantadine_ids)

        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Symadine')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('AMANTADINE')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Symmetrel')])

        valid_avapritinib_ids = {'CHEMBL4204794'}
        for t in self.entity_tagger.tag_entity('Avapritinib'):
            self.assertIn(t.entity_id, valid_avapritinib_ids)

    def test_chembl_entries_with_expansion(self):
        self.assertIn('CHEMBL1431', [t.entity_id for t in self.entity_tagger.tag_entity('LA-6023')])
        self.assertIn('CHEMBL1431', [t.entity_id for t in self.entity_tagger.tag_entity('Metformin')])

        self.assertIn('CHEMBL1064', [t.entity_id for t in self.entity_tagger.tag_entity('Simvastatin')])
        self.assertIn('CHEMBL1064', [t.entity_id for t in self.entity_tagger.tag_entity('SYNVINOLIN')])
        self.assertIn('CHEMBL1064', [t.entity_id for t in self.entity_tagger.tag_entity('Simvastatin hydroxy acid')])
        self.assertIn('CHEMBL1064', [t.entity_id for t in self.entity_tagger.tag_entity('MK-0733')])

        self.assertIn('CHEMBL1330792', [t.entity_id for t in self.entity_tagger.tag_entity('acetarsol')])

        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Amantadine')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Symadine')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('AMANTADINE')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Symmetrel')])

        self.assertIn('CHEMBL4204794', [t.entity_id for t in self.entity_tagger.tag_entity('Avapritinib')])

    def test_mesh_entries(self):
        """
        Tests whether MeSH entries can be tagged correctly
        :return:
        """
        self.assertIn('MESH:D003920', [t.entity_id for t in self.entity_tagger.tag_entity('Diabetes Mellitus')])

        valid_diabetes_2_tn = {'MESH:D003924'}
        diabetes_2_names = ['Diabetes Mellitus, Adult-Onset', 'Diabetes Mellitus, Ketosis-Resistant',
                            'Diabetes Mellitus, Maturity-Onset',
                            'Diabetes Mellitus, Non Insulin Dependent',
                            'Diabetes Mellitus, Non-Insulin-Dependent',
                            'Diabetes Mellitus, Noninsulin Dependent',
                            'Diabetes Mellitus, Noninsulin-Dependent',
                            'Diabetes Mellitus, Slow-Onset',
                            'Diabetes Mellitus, Stable',
                            'Diabetes Mellitus, Type II',
                            'MODY',
                            'Maturity-Onset Diabetes',
                            'Maturity-Onset Diabetes Mellitus',
                            'NIDDM',
                            'Noninsulin-Dependent Diabetes Mellitus',
                            'Type 2 Diabetes',
                            'Type 2 Diabetes Mellitus']
        for dn in diabetes_2_names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(dn)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_diabetes_2_tn)), len(valid_diabetes_2_tn))

        valid_neoplasms_ids = {'MESH:D009369'}
        neoplasms_terms = ['Neoplasms',
                           'Benign Neoplasms',
                           'Cancer',
                           'Malignancy',
                           'Malignant Neoplasms',
                           'Neoplasia',
                           'Neoplasm',
                           'Neoplasms, Benign',
                           'Tumors']
        for nt in neoplasms_terms:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(nt)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_neoplasms_ids)), len(valid_neoplasms_ids))

    def test_mesh_supplement_entries(self):
        self.assertIn('MESH:C535563', [t.entity_id for t in self.entity_tagger.tag_entity('Absence of Tibia')])

    def test_plant_families(self):
        """
        Tests whether plant family names can be tagged correctly
        """
        plant_families_in_db = []
        with open(PLANT_GENUS_DATABASE_FILE, 'rt') as f:
            plant_families_in_db = [line.strip() for line in f]

        for pf in plant_families_in_db:
            self.assertIn(pf.lower(), [t.entity_id.lower() for t in self.entity_tagger.tag_entity(pf)])

    def test_excipient_names(self):
        """
        Tests whether excipient names can be tagged correctly
        """
        excipient_names = [n for n in ExcipientVocabulary.read_excipients_names(expand_terms=False)]
        for en in excipient_names:
            if en.strip():
                eids = [t.entity_id.lower() for t in self.entity_tagger.tag_entity(en)]
                # If chembl is included then the excipient has been mapped to chembl.
                # We don't know the id here
                chembl_found = False
                for eid in eids:
                    if eid.startswith('chembl'):
                        chembl_found = True
                        break
                if not chembl_found:
                    self.assertIn(en.lower(), eids)

    def test_gene_names(self):
        valid_cyp3a4_symbol = {'cyp3a4'}
        cyp3a4_names = ['CYP3A4', 'cytochrome P450 family 3 subfamily A member 4',
                        'HLP', 'CP33', 'CP34', 'CYP3A', 'NF-25', 'CYP3A3',
                        'P450C3', 'CYPIIIA3', 'CYPIIIA4', 'P450PCN1']
        for n in cyp3a4_names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(n)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_cyp3a4_symbol)), len(valid_cyp3a4_symbol))

        valid_mtor_symbol = {'mtor'}
        mtor_names = ['MTOR', 'mechanistic target of rapamycin kinase', 'SKS', 'FRAP', 'FRAP1', 'FRAP2', 'RAFT1',
                      'RAPT1']
        for n in mtor_names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(n)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_mtor_symbol)), len(valid_mtor_symbol))

        valid_cyp3a5_symbol = {'cyp3a5'}
        cyp3a5_names = ['cyp3a5', 'cytochrome P450 family 3 subfamily A member 5',
                        'CP35', 'CYPIIIA5', 'P450PCN3', 'PCN3']
        for n in cyp3a5_names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(n)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_cyp3a5_symbol)), len(valid_cyp3a5_symbol))

    def test_nano_particle(self):
        valid_nano_particle_id = {'MESH:D053758'}
        names = ['nano particle', 'nano-particle', 'nano particles', 'nanoparticle', 'nanoparticles']
        for n in names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(n)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_nano_particle_id)), len(valid_nano_particle_id),
                                    msg=f'name: {n} failed - ids found: {found_ids}')

    def test_cell_line_names(self):
        valid_cell_line_id = {"CVCL_0023"}
        # A 549;A549;NCI-A549;A549/ATCC;A549 ATCC;A549ATCC;hA549
        names = ["A-549", "A 549", "A549", "NCI-A549", "A549/ATCC", "A549 ATCC", "A549ATCC", "hA549"]
        for n in names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(n)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_cell_line_id)), len(valid_cell_line_id),
                                    msg=f'name: {n} failed - ids found: {found_ids}')