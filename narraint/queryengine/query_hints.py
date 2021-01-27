import re

from narraint.entity.entity import Entity
from narraint.entity.enttypes import DISEASE, GENE, CHEMICAL, DOSAGE_FORM, EXCIPIENT, DRUG, DRUGBANK_CHEMICAL, SPECIES, \
    PLANT_FAMILY

QUERY_LIMIT = 50000
VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE_PREDICATE = re.compile(r'\((\w+),(\w+)\)')
VAR_TYPE = re.compile(r'\((\w+)\)')

ENTITY_TYPE_VARIABLE = "Variable"

MESH_ONTOLOGY = 'MESH_ONTOLOGY'

LIKE_SEARCH_FOR_ENTITY_TYPES = {DOSAGE_FORM, CHEMICAL, DISEASE, GENE, MESH_ONTOLOGY}

PREDICATE_ASSOCIATED = "associated"
DO_NOT_CARE_PREDICATE = PREDICATE_ASSOCIATED

ENTITY_TYPE_EXPANSION = dict(
    Chemical=[CHEMICAL, EXCIPIENT, DRUG, DRUGBANK_CHEMICAL]
)

PREDICATE_EXPANSION = dict(
    interacts=['interacts', 'metabolises', 'inhibits']
)

SYMMETRIC_PREDICATES = {"interacts", "associated", "induces", "decreases"}

PREDICATE_TYPING = {'treats': ({CHEMICAL, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT}, {DISEASE, SPECIES}),
                    'administered': ({DOSAGE_FORM}, {SPECIES, DISEASE, CHEMICAL, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT,
                                                     PLANT_FAMILY}),
                    'induces': ({CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY},
                                {CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY}),
                    'decreases': ({CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY},
                                  {CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY}),
                    'interacts': ({CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, GENE, PLANT_FAMILY},
                                  {CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, GENE, PLANT_FAMILY}),
                    'metabolises': ({GENE}, {CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, PLANT_FAMILY}),
                    'inhibits': ({CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, PLANT_FAMILY}, {GENE})
                    }


def sort_symmetric_arguments(subject_id, subject_type, object_id, object_type):
    if subject_id < object_id:
        return subject_id, subject_type, object_id, object_type
    else:
        return object_id, object_type, subject_id, subject_type


def have_entities_correct_order(arg1: Entity, arg2: Entity):
    return arg1.entity_id < arg2.entity_id


def should_perform_like_search_for_entity(entity_id, entity_type):
    if entity_type == DOSAGE_FORM and entity_id.lower().startswith('fidx'):
        return False
    if entity_type in LIKE_SEARCH_FOR_ENTITY_TYPES:
        return True
    else:
        return False
