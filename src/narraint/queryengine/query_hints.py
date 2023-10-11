import re

QUERY_LIMIT = 50000
VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE_PREDICATE = re.compile(r'\((\w+),(\w+)\)')
VAR_TYPE = re.compile(r'\((\w+/?\w+?)\)')

ENTITY_TYPE_VARIABLE = "Variable"

MESH_ONTOLOGY = 'MESH_ONTOLOGY'


PREDICATE_ASSOCIATED = "associated"
DO_NOT_CARE_PREDICATE = PREDICATE_ASSOCIATED


