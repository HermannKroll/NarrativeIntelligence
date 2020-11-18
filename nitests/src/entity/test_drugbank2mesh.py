from unittest import TestCase

from narraint.entity.drugbank2mesh import DrugBank2MeSHMapper


class ExtractionUtilsTestCase(TestCase):

    def test_drug_mappings(self):
        mapper = DrugBank2MeSHMapper.instance()
        # Metformin
        self.assertSetEqual({'MESH:D008687'}, mapper.dbid2meshid['DB00331'])
        # Simvastatin
        self.assertSetEqual({'MESH:D019821'}, mapper.dbid2meshid['DB00641'])
        # Erythromycin
        self.assertSetEqual({'MESH:D004917'}, mapper.dbid2meshid['DB00199'])
        # Amiodarone
        self.assertSetEqual({'MESH:D000638'}, mapper.dbid2meshid['DB01118'])
        # Clarithromycin
        self.assertSetEqual({'MESH:D017291'}, mapper.dbid2meshid['DB01211'])


