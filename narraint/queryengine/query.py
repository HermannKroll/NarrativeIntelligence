from narraint.entity.entity import Entity


class FactPattern:

    def __init__(self, subjects: Entity, predicate: str, objects: Entity):
        self.subjects = subjects
        self.predicate = predicate
        self.objects = objects

    def __str__(self):
        return '({}, {}, {})'.format(self.subjects, self.predicate, self.objects)

    def __repr__(self):
        return '({}, {}, {})'.format(self.subjects, self.predicate, self.objects)


class GraphQuery:

    def __init__(self):
        self.fact_patterns = []

    def add_fact_pattern(self, fact_pattern: FactPattern):
        self.fact_patterns.append(fact_pattern)

    def __iter__(self):
        for fp in self.fact_patterns:
            yield fp

    def __next__(self):
        for fp in self.fact_patterns:
            yield fp
