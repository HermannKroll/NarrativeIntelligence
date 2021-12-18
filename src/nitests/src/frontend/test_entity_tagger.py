from unittest import TestCase

from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.config import PLANT_FAMILTY_DATABASE_FILE
from narrant.vocabularies.excipient_vocabulary import ExcipientVocabulary


class EntityTaggerTestCase(TestCase):

    def setUp(self) -> None:
        self.entity_tagger = EntityTagger.instance()

    def test_drugbank_entries(self):
        """
        Tests whether drugbank names and headings can be tagged correctly
        """
        metformin_tags = self.entity_tagger.tag_entity('metformin')
        valid_metformin_ids = {'CHEMBL1431'}
        self.assertEqual(1, len(metformin_tags))
        for t in metformin_tags:
            self.assertIn(t.entity_id, valid_metformin_ids)
        self.assertIn('CHEMBL1431', [t.entity_id for t in self.entity_tagger.tag_entity('LA-6023')])
        self.assertIn('CHEMBL1431', [t.entity_id for t in self.entity_tagger.tag_entity('Metformin')])

        simvastatin_tags = self.entity_tagger.tag_entity('simvastatin')
        valid_simvastatin_ids = {'CHEMBL1064'}
        self.assertEqual(1, len(simvastatin_tags))
        for t in simvastatin_tags:
            self.assertIn(t.entity_id, valid_simvastatin_ids)

        self.assertEqual('CHEMBL1064', next(iter(self.entity_tagger.tag_entity('SYNVINOLIN'))).entity_id)
        self.assertEqual('CHEMBL1064', next(iter(self.entity_tagger.tag_entity('Simvastatin hydroxy acid'))).entity_id)
        self.assertEqual('CHEMBL1064', next(iter(self.entity_tagger.tag_entity('MK-0733'))).entity_id)

        acetarsol_tags = self.entity_tagger.tag_entity('acetarsol')
        valid_acetarsol_ids = {'CHEMBL1330792'}
        for t in acetarsol_tags:
            self.assertIn(t.entity_id, valid_acetarsol_ids)

        valid_amantadine_ids = {'CHEMBL660'}
        for t in self.entity_tagger.tag_entity('Amantadine'):
            self.assertIn(t.entity_id, valid_amantadine_ids)

        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Symadine')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('AMANTADINE')])
        self.assertIn('CHEMBL660', [t.entity_id for t in self.entity_tagger.tag_entity('Symmetrel')])

        valid_avapritinib_ids = {'CHEMBL4204794'}
        for t in self.entity_tagger.tag_entity('Avapritinib'):
            self.assertIn(t.entity_id, valid_avapritinib_ids)

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

    def test_plant_families(self):
        """
        Tests whether plant family names can be tagged correctly
        """
        plant_families_in_db = []
        with open(PLANT_FAMILTY_DATABASE_FILE, 'rt') as f:
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
                self.assertIn(en.lower(), [t.entity_id.lower() for t in self.entity_tagger.tag_entity(en)])

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
