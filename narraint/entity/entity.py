from narraint.entity.meshontology import MeSHOntology


class Entity:

    def __init__(self, entity_id, entity_type, entity_name=None):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.entity_name = entity_name

    def __hash__(self):
        return f'{self.entity_type}||{self.entity_id}'.__hash__()

    def __eq__(self, other):
        return other.entity_id == self.entity_id and other.entity_type == self.entity_type

    def __str__(self):
        return '{} ({})'.format(self.entity_id, self.entity_type)

    def __repr__(self):
        return '{} ({})'.format(self.entity_id, self.entity_type)

    def get_meshs(self) -> {str}:
        """
        Lookup all (sub-)mesh-descriptors, if type is 'MESH_ONTOLOGY'. Defaults to entity_id
        :return: {str}
        """
        mesh_ontology = MeSHOntology.instance()
        if self.entity_type == 'MESH_ONTOLOGY':
            mesh_descs = set(mesh_ontology.find_descriptors_start_with_tree_no(self.entity_id))
            return map(lambda d: 'MESH:{}'.format(d[0]), mesh_descs)
        else:
            return {self.entity_id}
