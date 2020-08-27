from collections import defaultdict

from narraint.entity.entityresolver import EntityResolver


class QueryEntitySubstitution:
    """
    Represents an entity substitution for a variable
    consists of: a string (inside the sentence), an entity id, an entity type and a name stemming from a vocabulary
    such as MeSH, NCBI Gene Vocabulary and Species Taxonomy
    """

    def __init__(self, entity_str, entity_id, entity_type, entity_name=None):
        self.entity_str = entity_str
        self.entity_id = entity_id
        self.entity_type = entity_type
        if not entity_name:
            self.entity_name = self._compute_entity_vocabulary_name()
        else:
            self.entity_name = entity_name

    def _compute_entity_vocabulary_name(self):
        """
        Uses the EntityResolver to find the vocabulary name/heading for the entity id and type
        :return:
        """
        entity_resolver = EntityResolver.instance()
        if self.entity_type == 'predicate':
            return self.entity_id  # id is already the name
        try:
            ent_name = entity_resolver.get_name_for_var_ent_id(self.entity_id, self.entity_type)
        except KeyError:
            ent_name = self.entity_str
        return ent_name

    def __str__(self):
        return '{} ("{}" "{}")'.format(self.entity_name, self.entity_id, self.entity_type)

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return dict(entity_name=self.entity_name, entity_str=self.entity_str, entity_id=self.entity_id,
                    entity_type=self.entity_type)


class QueryFactExplanation:
    """
    Represents a Fact explanation
    contains the sentence in which the fact is included, the cleaned predicate detected by OpenIE and the canonicalized
    version of the predicate
    """

    def __init__(self, position, sentence, predicate, predicate_canonicalized):
        self.position = position
        self.sentence = sentence
        self.predicate = predicate
        self.predicate_canonicalized = predicate_canonicalized

    def __str__(self):
        return '{} ("{}" -> "{}")'.format(self.sentence, self.predicate, self.predicate_canonicalized)

    def to_dict(self):
        return dict(sentence=self.sentence, predicate=self.predicate,
                    predicate_canonicalized=self.predicate_canonicalized)


class QueryResultBase:
    """
    Abstract class forming the foundation for the resulting structure
    """

    def to_dict(self):
        """
        Converts all internal attributes to a dictionary (needed for the JSON conversion)
        :return:
        """
        raise NotImplementedError

    def get_result_size(self):
        """
        Estimates the size of all contained results
        :return:
        """
        raise NotImplementedError


class QueryDocumentResult(QueryResultBase):
    """
    Represents document result
    """

    def __init__(self, document_id, title, var2substitution, confidence, explanations: [QueryFactExplanation]):
        self.document_id = document_id
        self.title = title
        self.var2substitution = var2substitution
        self.confidence = confidence
        self.explanations = explanations

    def integrate_explanation(self, explanation: QueryFactExplanation):
        """
        Integrates a explanation into the current list of explanations for this document and var substitution
        If the predicate and the sentence are already included as a explanation - the new explanation won't be added
        If the predicate is new but within the sentence, the predicate will be joined by a '/' into the existing list
        Else the new explanation will be added to the list
        :param explanation: a QueryFactExplanation for this document
        :return: None
        """
        for e in self.explanations:
            if e.position == explanation.position and e.sentence == explanation.sentence:
                if explanation.predicate in e.predicate:
                    return
                else:
                    e.predicate = e.predicate + '/' + explanation.predicate
                    return
        self.explanations.append(explanation)

    def to_dict(self):
        e_dict = [e.to_dict() for e in self.explanations]
        return dict(type="doc", document_id=self.document_id, title=self.title, explanations=e_dict)

    def get_result_size(self):
        return 1


class QueryDocumentResultList(QueryResultBase):
    """
    Represents a list of document results
    """

    def __init__(self):
        self.results = []

    def add_query_result(self, result: QueryResultBase):
        self.results.append(result)

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(type="doc_list", results=result_dict, size=self.get_result_size())

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])


class QueryResultAggregate(QueryResultBase):
    """
    Represents an aggregation for some variable substitution
    It includes a list of all aggregated results
    """

    def __init__(self, var2substitution):
        self.variable_names = sorted(list(var2substitution.keys()))
        self.var2substitution = var2substitution
        self.results = []

    def add_query_result(self, result: QueryResultBase):
        self.results.append(result)

    def _serialize_var_substitution(self):
        return {k: v.to_dict() for k, v in self.var2substitution.items()}

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(type="aggregate", size=self.get_result_size(), variable_names=self.variable_names,
                    substitution=self._serialize_var_substitution(), results=result_dict)

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])


class QueryResultAggregateList(QueryResultBase):
    """
    Represents a list of aggegrations
    """

    def __init__(self):
        self.results = []

    def add_query_result(self, result: QueryResultAggregate):
        self.results.append(result)

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(type="aggregate_list", results=result_dict, size=self.get_result_size())

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])

