from kgextractiontoolbox.cleaning.relation_type_constraints import RelationTypeConstraintStore
from kgextractiontoolbox.cleaning.relation_vocabulary import RelationVocabulary
from narrant.config import PHARM_RELATION_VOCABULARY, PHARM_RELATION_CONSTRAINTS
from narraint.frontend.entity.query_translation import QueryTranslation
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES


class SchemaGraph:

    def __init__(self):
        self.__load_schema_graph()

    def __load_schema_graph(self):
        translation = QueryTranslation()
        self.entity_types = translation.variable_type_mappings
        # print(self.entity_types)
        self.max_spaces_in_entity_types = max([len(t.split(' ')) - 1 for t in self.entity_types])
        print(f'Longest entity type has {self.max_spaces_in_entity_types} spaces')
        self.relation_vocab = RelationVocabulary()
        self.relation_vocab.load_from_json(PHARM_RELATION_VOCABULARY)
        print(f'Relation vocab with {len(self.relation_vocab.relation_dict)} relations load')
        self.relation_dict = {k: k for k in self.relation_vocab.relation_dict.keys()}
        self.relation_dict.update({syn: k for k, synonyms in self.relation_vocab.relation_dict.items()
                                   for syn in synonyms})
        # print(self.relation_dict)

        print('Load relation constraint file...')
        self.relation_type_constraints = RelationTypeConstraintStore()
        self.relation_type_constraints.load_from_json(PHARM_RELATION_CONSTRAINTS)
        self.relations = self.relation_dict.keys()

        self.symmetric_relations = SYMMETRIC_PREDICATES
        print('Finished')

    def find_possible_relations_for_entity_types(self, subject_type, object_type):
        allowed_relations = set()
        for r in self.relations:
            # If the relation is constrained, check the constraints
            if r in self.relation_type_constraints.constraints:
                s_const = subject_type in self.relation_type_constraints.get_subject_constraints(r)
                o_const = object_type in self.relation_type_constraints.get_object_constraints(r)
                if s_const and o_const:
                    allowed_relations.add(r)
            else:
                # It is not constrained - so it does work
                allowed_relations.add(r)
        return allowed_relations
