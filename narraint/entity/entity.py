
class Entity:

    def __init__(self, entity_id, entity_type, entity_name=None):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.entity_name = entity_name

    def __str__(self):
        return '{} ({})'.format(self.entity_id, self.entity_type)

    def __repr__(self):
        return '{} ({})'.format(self.entity_id, self.entity_type)
