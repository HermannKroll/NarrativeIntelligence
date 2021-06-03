from unittest import TestCase

from narraint.config import PLANT_FAMILTY_DATABASE_FILE
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.preprocessing.tagging.vocabularies import ExcipientVocabulary


class EntityTaggerTestCase(TestCase):

    def setUp(self) -> None:
        self.entity_tagger = EntityTagger.instance()

    def test_drugbank_entries(self):
        """
        Tests whether drugbank names and headings can be tagged correctly
        """
        metformin_tags = self.entity_tagger.tag_entity('metformin')
        valid_metformin_ids = {'DB00331'}
        self.assertEqual(1, len(metformin_tags))
        for t in metformin_tags:
            self.assertIn(t.entity_id, valid_metformin_ids)
        self.assertEqual('DB00331', next(iter(self.entity_tagger.tag_entity('metformine'))).entity_id)
        self.assertEqual('DB00331', next(iter(self.entity_tagger.tag_entity('Metforminum'))).entity_id)
        self.assertEqual('DB00331', next(iter(self.entity_tagger.tag_entity('Dimethylbiguanid'))).entity_id)
        self.assertEqual('DB00331', next(iter(self.entity_tagger.tag_entity('dimethylbiguanid'))).entity_id)

        simvastatin_tags = self.entity_tagger.tag_entity('simvastatin')
        valid_simvastatin_ids = {'DB00641'}
        self.assertEqual(1, len(simvastatin_tags))
        for t in simvastatin_tags:
            self.assertIn(t.entity_id, valid_simvastatin_ids)

        self.assertEqual('DB00641', next(iter(self.entity_tagger.tag_entity('Simvastatinum'))).entity_id)
        self.assertEqual('DB00641', next(iter(self.entity_tagger.tag_entity('Simvastatina'))).entity_id)
        self.assertEqual('DB00641', next(iter(self.entity_tagger.tag_entity(
            '2,2-dimethylbutyric acid, 8-ester with (4R,6R)-6-(2-((1S,2S,6R,8S,8aR)-1,2,6,7,8,8a-hexahydro-8-hydroxy-2,6-dimethyl-1-naphthyl)ethyl)tetrahydro-4-hydroxy-2H-pyran-2-one'))).entity_id)

        acetarsol_tags = self.entity_tagger.tag_entity('acetarsol')
        valid_acetarsol_ids = {'DB13268', 'MESH:C005284'}
        for t in acetarsol_tags:
            self.assertIn(t.entity_id, valid_acetarsol_ids)

        valid_amantadine_ids = {'D02.455.426.100.050.035', 'DB00915'}
        for t in self.entity_tagger.tag_entity('Amantadine'):
            self.assertIn(t.entity_id, valid_amantadine_ids)

        self.assertEqual('DB00915', next(iter(self.entity_tagger.tag_entity('1-adamantanamine'))).entity_id)
        self.assertEqual('DB00915', next(iter(self.entity_tagger.tag_entity('Amantadina'))).entity_id)
        self.assertEqual('DB00915', next(iter(self.entity_tagger.tag_entity('Amantadinum'))).entity_id)
        self.assertEqual('DB00915', next(iter(self.entity_tagger.tag_entity('Aminoadamantane'))).entity_id)

        valid_avapritinib_ids = {'MESH:C000707147', 'DB15233'}
        for t in self.entity_tagger.tag_entity('Avapritinib'):
            self.assertIn(t.entity_id, valid_avapritinib_ids)

    def test_mesh_entries(self):
        """
        Tests whether MeSH entries can be tagged correctly
        :return:
        """
        valid_diabetes_tn = {'C18.452.394.750', 'C19.246'}
        for t in self.entity_tagger.tag_entity('Diabetes Mellitus'):
            self.assertIn(t.entity_id, valid_diabetes_tn)

        valid_diabetes_2_tn = {'C18.452.394.750.149', 'C19.246.300'}
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

        valid_neoplasms_ids = {'C04'}
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
        valid_nano_particle_id = {'J01.637.512.600'}
        names = ['nano particle', 'nano-particle', 'nano particles', 'nanoparticle', 'nanoparticles']
        for n in names:
            found_ids = set([t.entity_id for t in self.entity_tagger.tag_entity(n)])
            self.assertGreaterEqual(len(found_ids.intersection(valid_nano_particle_id)), len(valid_nano_particle_id),
                                    msg=f'name: {n} failed - ids found: {found_ids}')
