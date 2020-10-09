from narraint.entity.enttypes import DISEASE, GENE, CHEMICAL, DOSAGE_FORM

LIKE_SEARCH_FOR_ENTITY_TYPES = {DOSAGE_FORM, CHEMICAL, DISEASE, GENE}

DO_NOT_CARE_PREDICATE = 'associated'


PREDICATE_EXPANSION = dict(
    interacts=['interacts', 'metabolises', 'inhibits']
)

SYMMETRIC_PREDICATES = {"interacts", "administered"}
