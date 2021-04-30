from unittest import TestCase

from narrant.entity.drugbank2mesh import DrugBank2MeSHMapper


class DrugBank2MeSHTestCase(TestCase):

    def test_drug_mappings(self):
        mapper = DrugBank2MeSHMapper.instance()
        # Metformin
        self.assertEqual('MESH:D008687', mapper.dbid2meshid['DB00331'])
        # Simvastatin
        self.assertEqual('MESH:D019821', mapper.dbid2meshid['DB00641'])
        # Erythromycin
        self.assertEqual('MESH:D004917', mapper.dbid2meshid['DB00199'])
        # Amiodarone
        self.assertEqual('MESH:D000638', mapper.dbid2meshid['DB01118'])
        # Clarithromycin
        self.assertEqual('MESH:D017291', mapper.dbid2meshid['DB01211'])


