from narraint.entity.enttypes import DISEASE, GENE, CHEMICAL, DOSAGE_FORM

MESH_ONTOLOGY = 'MESH_ONTOLOGY'

LIKE_SEARCH_FOR_ENTITY_TYPES = {DOSAGE_FORM, CHEMICAL, DISEASE, GENE, MESH_ONTOLOGY}

DO_NOT_CARE_PREDICATE = 'associated'


PREDICATE_EXPANSION = dict(
    interacts=['interacts', 'metabolises', 'inhibits']
)

SYMMETRIC_PREDICATES = {"interacts", "administered"}


def should_perform_like_search_for_entity(entity_id, entity_type):
    if entity_type == DOSAGE_FORM and entity_id.lower().startswith('fidx'):
        return False
    if entity_type in LIKE_SEARCH_FOR_ENTITY_TYPES:
        return True
    else:
        return False
