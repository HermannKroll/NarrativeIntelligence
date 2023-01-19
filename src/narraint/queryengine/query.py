from narraint.queryengine.query_hints import ENTITY_TYPE_VARIABLE, VAR_NAME
from narrant.entity.entity import Entity


class FactPattern:

    def __init__(self, subjects: [Entity], predicate: str, objects: [Entity]):
        self.subjects = subjects
        self.predicate = predicate
        self.objects = objects

    def has_variable(self):
        for s in self.subjects:
            if s.entity_type == ENTITY_TYPE_VARIABLE:
                return True
        for o in self.objects:
            if o.entity_type == ENTITY_TYPE_VARIABLE:
                return True
        return False

    def get_flipped(self):
        return FactPattern(self.objects, self.predicate, self.subjects)

    def get_subject_class(self):
        for s in self.subjects:
            if s.entity_class:
                return s.entity_class
        return None

    def get_object_class(self):
        for o in self.objects:
            if o.entity_class:
                return o.entity_class
        return None

    def has_entity(self):
        for s in self.subjects:
            if s.entity_type != ENTITY_TYPE_VARIABLE:
                return True
        for o in self.objects:
            if o.entity_type != ENTITY_TYPE_VARIABLE:
                return True
        return False

    def get_variable_names(self):
        var_names = []
        for s in self.subjects:
            if s.entity_type == ENTITY_TYPE_VARIABLE:
                var_names.append(VAR_NAME.search(s.entity_id).group(1))
        for o in self.objects:
            if o.entity_type == ENTITY_TYPE_VARIABLE:
                var_names.append(VAR_NAME.search(o.entity_id).group(1))
        return var_names

    def __eq__(self, other):
        if self.predicate != other.predicate:
            return False
        s1_subs = {s for s in self.subjects}
        s2_subs = {s for s in other.subjects}
        if len(s1_subs.intersection(s2_subs)) != len(s1_subs):
            return False
        o1_subs = {o for o in self.objects}
        o2_subs = {o for o in other.objects}
        if len(o1_subs.intersection(o2_subs)) != len(o1_subs):
            return False
        return True

    def __str__(self):
        return '({}, {}, {})'.format(self.subjects, self.predicate, self.objects)

    def __repr__(self):
        return '({}, {}, {})'.format(self.subjects, self.predicate, self.objects)

    def to_dict(self):
        return dict(subjects=[s.to_dict() for s in self.subjects],
                    relation=self.predicate,
                    objects=[o.to_dict() for o in self.objects])


class GraphQuery:

    def __init__(self, fact_patterns=None):
        if fact_patterns is None:
            self.fact_patterns = list()
        else:
            self.fact_patterns = fact_patterns

        self.entity_sets = list()
        self.terms = set()

    def has_terms(self):
        return len(self.terms) > 0

    def has_entities(self) -> bool:
        return len(self.entity_sets) > 0

    def has_entity(self):
        for fp in self.fact_patterns:
            if fp.has_entity():
                return True
        return False

    def add_fact_pattern(self, fact_pattern: FactPattern):
        self.fact_patterns.append(fact_pattern)

    def add_entity(self, entity_ids):
        self.entity_sets.append(list(entity_ids))

    def add_term(self, term):
        self.terms.add(term.lower().strip())

    def __iter__(self):
        for fp in self.fact_patterns:
            yield fp

    def __next__(self):
        for fp in self.fact_patterns:
            yield fp

    def __str__(self):
        query_str = ["<Statements: ", ' AND '.join([str(fp) for fp in self.fact_patterns]), '>']
        if self.has_entities():
            query_str.extend([' <Entities:', ' AND '.join([str(e) for e in self.entity_sets]), '>'])
        if self.has_terms():
            query_str.extend([' <Terms:', ' AND '.join([str(t) for t in self.terms]), '>'])
        return ' '.join([str(p) for p in query_str])

    def get_unique_key(self):
        parts = []
        for fp in self.fact_patterns:
            parts.extend(sorted([s.entity_id for s in fp.subjects]))
            parts.append(fp.predicate)
            parts.extend(sorted([o.entity_id for o in fp.objects]))

        for ae in self.entity_sets:
            parts.extend(sorted([e.entity_id for e in ae]))
        if self.has_terms():
            parts.extend(sorted([t for t in self.terms]))
        return '_'.join(parts)

    def get_var_names_in_order(self):
        var_names = []
        for fp in self.fact_patterns:
            for var_name in fp.get_variable_names():
                if var_name not in var_names:
                    var_names.append(var_name)
        return var_names

    def to_dict(self):
        return dict(fact_patterns=[fp.to_dict() for fp in self.fact_patterns],
                    entities=list([str(e) for e in self.entity_sets]),
                    terms=list(self.terms))
