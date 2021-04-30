from unittest import TestCase

from narraint.config import MESH_SUPPLEMENTARY_FILE
from narrant.mesh.supplementary import MeSHDBSupplementary


class Test(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db : MeSHDBSupplementary = MeSHDBSupplementary.instance()
        cls.db.load_xml(MESH_SUPPLEMENTARY_FILE)

    def test_record_values(self):
        record = self.db.record_by_id('C114158')
        self.assertEqual('quantum dye macrocyclic europium-chelate', record.name)

        allowed_terms = ["quantum dye macrocyclic europium-chelate", "QD macrocyclic",
                         "quantum dye macrocyclic europium-chelate"]
        record_terms = record.terms
        for t in record_terms:
            self.assertIn(t.string, allowed_terms)

        concepts = record.concepts
        self.assertEqual(1, len(concepts))
        self.assertEqual("M0294520", concepts[0].concept_ui)
        self.assertEqual("quantum dye macrocyclic europium-chelate", concepts[0].name)

        self.assertEqual("a macrocyclic europium-chelate; structure in first source", record.note)

        headings_mapped_to = record.headings_mapped_to
        self.assertEqual(2, len(headings_mapped_to))
        self.assertEqual("*D005063", headings_mapped_to[0].unique_id)
        self.assertEqual("Europium", headings_mapped_to[0].name)

        self.assertEqual("*D009942", headings_mapped_to[1].unique_id)
        self.assertEqual("Organometallic Compounds", headings_mapped_to[1].name)

    def test_record_by_id(self):
        record = self.db.record_by_id('C114158')
        self.assertEqual('quantum dye macrocyclic europium-chelate', record.name)

        record = self.db.record_by_id('C008718')
        self.assertEqual('osteoclast activating factor', record.name)

    def test_record_by_name(self):
        records = self.db.records_by_name("quantum dye macrocyclic europium-chelate", search_terms=False)
        self.assertEqual(1, len(records))
        record = records[0]
        self.assertEqual('C114158', record.unique_id)
        self.assertEqual('quantum dye macrocyclic europium-chelate', record.name)