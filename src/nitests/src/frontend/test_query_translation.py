from unittest import TestCase

from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import EntityTaggerData
from narraint.frontend.entity.query_translation import QueryTranslation
from narrant.entitylinking.enttypes import PLANT_FAMILY_GENUS

tagger_entries = {
    ('MESH:D007267', 'DosageForm', None, ' injection'),
    ('CHEMBL1064', 'Drug', None, ' simvastatin'),
    ('CHEMBL1431', 'Drug', None, ' metformin'),
    ('9606', 'Species', None, ' human'),
    ('MESH:D003920', 'Disease', None, ' diabetes mellitus')
}


class QueryTranslationTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        session = SessionExtended.get()
        # Delete old tagger data
        session.execute(delete(EntityTaggerData))
        session.commit()

        entity_tagger_data = list()
        for ent_id, ent_type, ent_class, synonyms in tagger_entries:
            entity_tagger_data.append(dict(entity_id=ent_id,
                                           entity_type=ent_type,
                                           entity_class=ent_class,
                                           synonym=synonyms,
                                           synonym_processed=synonyms))

        EntityTaggerData.bulk_insert_values_into_table(session, entity_tagger_data)

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

        self.assertIsNotNone(graph_query, msg=text)
        self.assertTrue(graph_query.has_entities())
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
        self.assertFalse(graph_query.has_entities())
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


def generate_test_data():
    from narraint.frontend.entity.entitytagger import EntityTagger

    import tqdm

    tagger_data = set()
    entity_tagger = EntityTagger()

    terms_to_explain = {
        "metformin",
        "human",
        "diabetes mellitus",
        "simvastatin",
        "injection"
    }

    known_terms = set()
    for term in tqdm.tqdm(terms_to_explain):
        for entity in entity_tagger.tag_entity(term):
            if entity.entity_name not in terms_to_explain or entity.entity_name in known_terms:
                continue
            known_terms.add(entity.entity_name)
            tagger_data.add((entity.entity_id, entity.entity_type, entity.entity_class, " " + entity.entity_name))

    print("tagger_entries = {\n" + ",\n".join("\t" + str(t) for t in list(tagger_data)) + "\n}")


if __name__ == "__main__":
    generate_test_data()
