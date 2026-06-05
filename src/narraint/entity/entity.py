from narrant.entity.entity import Entity


class TranslatedEntity(Entity):


    def __init__(self, entity_id, entity_type, translation_score: float, entity_name=None, entity_class=None):
        super().__init__(entity_id, entity_type, entity_name, entity_class)
        self.translation_score = translation_score