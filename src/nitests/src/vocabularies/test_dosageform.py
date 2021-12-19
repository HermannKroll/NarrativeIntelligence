import unittest

from narrant.preprocessing.pharmacy.dosage import DosageFormTagger
from nitests.util import create_test_kwargs


class TestDosageFormVocabulary(unittest.TestCase):

    def setUp(self) -> None:
        self.tagger = DosageFormTagger(**create_test_kwargs())
        self.tagger.prepare()

    def test_additional_mesh_descs(self):
        self.assertIn('MESH:D000280', self.tagger.desc_by_term['inhalation of drugs'])
        self.assertIn('MESH:D008845', self.tagger.desc_by_term['microinjections'])

    def test_mesh_trees(self):
        self.assertIn('MESH:D004337', self.tagger.desc_by_term['drug carriers'])
        self.assertIn('MESH:D053769', self.tagger.desc_by_term['nanocapsules'])

    def test_additional_mesh_synonyms(self):
        self.assertIn('MESH:D022701', self.tagger.desc_by_term['virosomes'])
        self.assertIn('MESH:D059085', self.tagger.desc_by_term['nose spray'])
        self.assertIn('MESH:D043942', self.tagger.desc_by_term['nano rods'])

    def test_fid_descriptors(self):
        self.assertIn('FIDX9', self.tagger.desc_by_term['granulate'])
        self.assertIn('FIDX9', self.tagger.desc_by_term['instant granules'])
        self.assertIn('FIDX11', self.tagger.desc_by_term['dry syrup'])

    def test_dosage_form_rules(self):
        self.assertIn('MESH:D053769', self.tagger.desc_by_term['nanocapsules'])
        self.assertIn('MESH:D053769', self.tagger.desc_by_term['nanocapsule'])
        self.assertIn('MESH:D053769', self.tagger.desc_by_term['nano-capsules'])
        self.assertIn('MESH:D053769', self.tagger.desc_by_term['nano capsule'])
        self.assertIn('MESH:D053769', self.tagger.desc_by_term['nano capsules'])

        self.assertIn('FIDX26', self.tagger.desc_by_term['microneedle'])
        self.assertIn('FIDX26', self.tagger.desc_by_term['micro-needle'])
        self.assertIn('FIDX26', self.tagger.desc_by_term['micro-needles'])

        self.assertIn('FIDX25', self.tagger.desc_by_term['intrauterine device'])
        self.assertIn('FIDX25', self.tagger.desc_by_term['intra-uterine device'])
        self.assertIn('FIDX25', self.tagger.desc_by_term['intra uterine device'])
