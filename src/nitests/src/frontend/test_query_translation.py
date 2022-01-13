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
