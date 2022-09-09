from unittest import TestCase

from narraint.frontend.entity.query_translation import QueryTranslation
from narrant.preprocessing.enttypes import PLANT_FAMILY_GENUS


class QueryTranslationTestCase(TestCase):

    def setUp(self) -> None:
        self.translation = QueryTranslation()

    def test_translate_plant_family_synonyms(self):
        plant_synonyms = ["?X(PlantFamily)", "?X(PlantGenus)", "?X(plantfamilies)",
                          "?X(plantgenus)", "?X(plantgenera)"]

        for ps in plant_synonyms:
            _, entity_type = self.translation.check_and_convert_variable(ps)
            self.assertEqual(entity_type, PLANT_FAMILY_GENUS)

    def test_convert_json_to_fact_patterns(self):
        # AND-Query having additional entities
        json = r'''{
            "fact_patterns": [
                {
                    "subject": "Metformin",
                    "predicate": "associated",
                    "object": "Human"
                },
                {
                    "subject": "Metformin",
                    "predicate": "treats",
                    "object": "Diabetes Mellitus"
                }
            ],
            "entities": [
                "injection"
            ]
        }'''

        graph_query, text = self.translation.convert_json_to_fact_patterns(json)

        self.assertIsNotNone(graph_query)
        self.assertTrue(graph_query.has_additional_entities())
        self.assertEqual(len(graph_query.to_dict()["fact_patterns"]), 2)

        # AND-Query without additional entities
        json = r'''{
            "fact_patterns": [
                {
                    "subject": "Metformin",
                    "predicate": "associated",
                    "object": "Human"
                },
                {
                    "subject": "Metformin",
                    "predicate": "treats",
                    "object": "Diabetes Mellitus"
                }]
        }'''
        graph_query, text = self.translation.convert_json_to_fact_patterns(json)

        self.assertIsNotNone(graph_query)
        self.assertFalse(graph_query.has_additional_entities())
        self.assertEqual(len(graph_query.to_dict()["fact_patterns"]), 2)

        # Object missing in query pattern
        json = r'''{
            "fact_patterns": [
                {
                    "subject": "Simvastatin",
                }]
        }'''
        graph_query, text = self.translation.convert_json_to_fact_patterns(json)
        self.assertIsNone(graph_query)

        # Predicate missing in query pattern
        json = r'''{
                    "fact_patterns": [
                        {
                            "subject": "Metformin",
                            "object": "Diabetes Mellitus"
                        }]
                }'''
        graph_query, text = self.translation.convert_json_to_fact_patterns(json)
        self.assertIsNone(graph_query)

        # Subject missing in query pattern
        json = r'''{
                    "fact_patterns": [
                        {
                            "predicate": "associated",
                            "object": "Diabetes Mellitus"
                        }]
                }'''
        graph_query, text = self.translation.convert_json_to_fact_patterns(json)
        self.assertIsNone(graph_query)

        # Invalid JSON pattern ("," after Diabetes Mellitus)
        json = r'''{
                    "fact_patterns": [
                        {
                            "subject": "Metformin",
                            "predicate": "associated",
                            "object": "Diabetes Mellitus",
                        }]
                }'''
        graph_query, text = self.translation.convert_json_to_fact_patterns(json)
        self.assertIsNone(graph_query)
