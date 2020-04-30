from collections import defaultdict

from narraint.entity.entityresolver import EntityResolver


class QueryEntitySubstitution:

    def __init__(self, entity_str, entity_id, entity_type):
        self.entity_str = entity_str
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.entity_name = self._compute_entity_vocabulary_name()

    def _compute_entity_vocabulary_name(self):
        entity_resolver = EntityResolver.instance()
        if self.entity_type == 'predicate':
            return self.entity_id  # id is already the name
        try:
            ent_name = entity_resolver.get_name_for_var_ent_id(self.entity_id, self.entity_type)
        except KeyError:
            ent_name = self.entity_str
        return ent_name

    def to_dict(self):
        return dict(entity_name=self.entity_name, entity_str=self.entity_str, entity_id=self.entity_id,
                    entity_type=self.entity_type)


class QueryFactExplanation:

    def __init__(self, sentence, predicate, predicate_canonicalized):
        self.sentence = sentence
        self.predicate = predicate
        self.predicate_canonicalized = predicate_canonicalized

    def __str__(self):
        return '{} ("{}" -> "{}")'.format(self.sentence, self.predicate, self.predicate_canonicalized)

    def to_dict(self):
        return dict(sentence=self.sentence, predicate=self.predicate,
                    predicate_canonicalized=self.predicate_canonicalized)


def serialize_var_substitution(var2substitution):
    return {k: v.to_dict() for k, v in var2substitution.items()}


class QueryResultBase:
    pass

    def to_dict(self):
        raise NotImplementedError


class QueryResult(QueryResultBase):

    def __init__(self, document_id, title, var2substitution, confidence, explanations: [QueryFactExplanation]):
        self.document_id = document_id
        self.title = title
        self.var2substitution = var2substitution
        self.confidence = confidence
        self.explanations = explanations

    def to_dict(self):
        e_dict = [e.to_dict() for e in self.explanations]
        return dict(type="result", document_id=self.document_id, title=self.title, explanations=e_dict)


class QueryResultAggregate(QueryResultBase):

    def __init__(self, var2substitution):
        self.variable_names = sorted(list(var2substitution.keys()))
        self.var2substitution = var2substitution
        self.results = []

    def add_query_result(self, result: QueryResultBase):
        self.results.append(result)

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(type="aggregate", result_size=len(self.results), variable_names=self.variable_names,
                    substitution=serialize_var_substitution(self.var2substitution), results=result_dict)


class QueryResultAggregateList(QueryResultBase):

    def __init__(self):
        self.results = []

    def add_query_result(self, result: QueryResultAggregate):
        self.results.append(result)

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(type="aggregate_list", results=result_dict, result_size=len(self.results))


class QueryResultList(QueryResultBase):

    def __init__(self):
        self.results = []

    def add_query_result(self, result: QueryResultBase):
        self.results.append(result)

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(type="result_list", results=result_dict, result_size=len(self.results))
