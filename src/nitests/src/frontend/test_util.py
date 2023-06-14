from unittest import TestCase

from narraint.frontend.entity.util import explain_concept_translation


class TestUtil(TestCase):

    def test_explain_concept_prefix_filter(self):
        headings = explain_concept_translation("Diabetes")
        self.assertIn("Diabetes Mellitus", headings)
        self.assertNotIn("Diabetes Mellitus Type 1", headings)
        self.assertNotIn("Diabetes Mellitus Type 2", headings)

        headings = explain_concept_translation("Covid 19")
        self.assertIn("COVID-19", headings)
        self.assertNotIn("COVID-19 Drug Treatment", headings)
        self.assertNotIn("COVID-19 Testing", headings)

    def test_explain_concept_to_large(self):
        headings = explain_concept_translation("Disease")
        self.assertEqual(1, len(headings))
