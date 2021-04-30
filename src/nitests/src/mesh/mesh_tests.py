from unittest import TestCase

from narraint.config import MESH_DESCRIPTORS_FILE
from narrant.mesh.data import MeSHDB


class Test(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db = MeSHDB.instance()
        cls.db.load_xml(MESH_DESCRIPTORS_FILE, verbose=True)

    def test_tree_numbers(self):
        desc1 = self.db.desc_by_id("D000001")
        self.assertListEqual(desc1.tree_numbers, ["D03.633.100.221.173"])
        desc2 = self.db.desc_by_id("D019821")  # Simvastatin
        self.assertListEqual(desc2.tree_numbers, ["D02.455.426.559.847.638.400.900", "D04.615.638.400.900"])

    def test_parents_one_parent(self):
        desc = self.db.desc_by_tree_number("D03.383.082")
        parent1 = self.db.desc_by_tree_number("D03.383")
        self.assertListEqual(desc.parents, [parent1])

    def test_parents_two_parents(self):
        desc = self.db.desc_by_id("D011084")  # Polycyclic Aromatic Hydrocarbons
        parent21 = self.db.desc_by_tree_number("D02.455.426.559")
        parent22 = self.db.desc_by_tree_number("D04")
        self.assertListEqual(desc.parents, [parent21, parent22])

    def test_parents_no_parent(self):
        desc = self.db.desc_by_id("D009930")  # Organic chemicals
        self.assertListEqual(desc.parents, [])

    def test_desc_by_tree_number(self):
        desc11 = self.db.desc_by_tree_number("D04.615.638.400")  # Lovastatin
        desc12 = self.db.desc_by_id("D008148")
        self.assertEqual(desc11, desc12)
        desc21 = self.db.desc_by_tree_number("D02.455.426.559.847.638.400.900")
        desc22 = self.db.desc_by_tree_number("D04.615.638.400.900")
        self.assertEqual(desc21, desc22)

    def test_lineages(self):
        pivot = self.db.desc_by_id("D011084")
        parent01 = self.db.desc_by_tree_number("D04")
        parent02 = self.db.desc_by_tree_number("D02.455.426.559")
        parent021 = self.db.desc_by_tree_number("D02.455.426")
        parent0211 = self.db.desc_by_tree_number("D02.455")
        parent02111 = self.db.desc_by_tree_number("D02")
        lg1 = [parent01, pivot]
        lg2 = [parent02111, parent0211, parent021, parent02, pivot]
        lineages = pivot.lineages
        self.assertListEqual(lineages, [lg2, lg1])

    def test_get_common_lineage(self):
        desc1 = self.db.desc_by_id("D006841")  # Hydrocarbons, Aromatic
        desc2 = self.db.desc_by_id("D011084")  # Polycyclic Aromatic Hydrocarbons
        a1 = self.db.desc_by_tree_number("D02.455.426")
        a2 = self.db.desc_by_tree_number("D02.455")
        a3 = self.db.desc_by_tree_number("D02")
        expected_common_lineage = [[a3, a2, a1, desc1]]
        common_lineage = desc1.get_common_lineage(desc2)
        self.assertListEqual(common_lineage, expected_common_lineage)

    def test_descs_under_tree_number_one_child(self):
        desc = self.db.desc_by_id("D019284")  # Thapsigargin
        descs = self.db.descs_under_tree_number("D02.455.426.392.368.284.500")
        self.assertListEqual(descs, [desc])

    def test_descs_under_tree_number_multiple_children(self):
        descs = self.db.descs_under_tree_number("D02.455.426.392.368.242.888")
        c1 = self.db.desc_by_tree_number("D02.455.849.291.850.389")
        c2 = self.db.desc_by_tree_number("D02.455.426.392.368.242.888.777")
        c3 = self.db.desc_by_tree_number("D02.455.426.392.368.242.888.777.500")
        self.assertListEqual(descs, sorted([c1, c2, c3]))

    def test_desc_qualifiers(self):
        desc1 = self.db.desc_by_id('D019454')
        allowed_qualifiers = {'Q000662', 'Q000639', 'Q000706', 'Q000592', 'Q000523', 'Q000451',
                              'Q000401', 'Q000379', 'Q000295', 'Q000266', 'Q000941', 'Q000191',
                              'Q000145', 'Q000009'}
        self.assertEqual(len(desc1.allowable_qualifiers_list), 14)
        for q in desc1.allowable_qualifiers_list:
            self.assertIn(q.qualifier_ui, allowed_qualifiers)