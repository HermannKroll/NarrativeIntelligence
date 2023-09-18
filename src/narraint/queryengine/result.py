from typing import Dict, Set

from narrant.entity.entityresolver import EntityResolver


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
            ent_name = entity_resolver.get_name_for_var_ent_id(self.entity_id, self.entity_type,
                                                               resolve_gene_by_id=False)
        except KeyError:
            ent_name = self.entity_str if self.entity_str else self.entity_id
        if ent_name == self.entity_id and self.entity_str:
            ent_name = self.entity_str
        return ent_name

    def __str__(self):
        return '{} ("{}" "{}")'.format(self.entity_name, self.entity_id, self.entity_type)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, QueryEntitySubstitution):
            if other.entity_type == self.entity_type and other.entity_id == self.entity_id and \
                    other.entity_str == self.entity_str and other.entity_name == self.entity_name:
                return True
            else:
                return False
        else:
            return False

    def __hash__(self):
        return hash((self.entity_id, self.entity_type))

    def to_dict(self):
        return dict(n=self.entity_name, s=self.entity_str, id=self.entity_id,
                    t=self.entity_type)


class QueryFactExplanation:
    """
    Represents a Fact explanation
    contains the sentence in which the fact is included, the cleaned predicate detected by OpenIE and the canonicalized
    version of the predicate
    """

    def __init__(self, position, sentence, predicate, relation, subject_str, object_str, confidence,
                 predication_id):
        self.position = position
        self.sentence = sentence
        self.predicate = predicate
        self.relation = relation
        self.subject_str = subject_str
        self.object_str = object_str
        self.confidence = round(confidence, 2)
        self.predication_ids = {predication_id}

    def __str__(self):
        return '{} [{}, "{}" -> "{}", {}]'.format(self.sentence, self.subject_str, self.predicate,
                                                  self.relation, self.object_str)

    def to_dict(self):
        return dict(s=self.sentence, p=self.predicate,
                    p_c=self.relation,
                    s_str=self.subject_str, o_str=self.object_str, pos=self.position, conf=self.confidence,
                    ids=','.join([str(i) for i in self.predication_ids]))


class QueryExplanation:

    def __init__(self):
        self.explanations = []

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
                e.predication_ids.update(explanation.predication_ids)
                if explanation.predicate not in e.predicate:
                    e.predicate = e.predicate + '//' + explanation.predicate
                if explanation.subject_str not in e.subject_str:
                    e.subject_str = e.subject_str + '//' + explanation.subject_str
                if explanation.object_str not in e.object_str:
                    e.object_str = e.object_str + '//' + explanation.object_str
                return
        self.explanations.append(explanation)
        self.explanations.sort(key=lambda x: x.position)

    def to_dict(self):
        self.explanations.sort(key=lambda x: x.position)
        e_dict = [e.to_dict() for e in self.explanations]
        return dict(exp=e_dict)


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

    def __init__(self, document_id: int, title: str, authors: str, journals: str, publication_year: int,
                 publication_month: int, var2substitution, confidence, position2provenance_ids: Dict[int, Set[int]],
                 org_document_id: str = None, doi: str = None, document_collection: str = None,
                 document_classes: [str] = None):
        self.document_id = document_id
        self.title = title
        self.journals = journals
        self.authors = authors
        self.publication_year = publication_year
        self.publication_month = publication_month
        self.var2substitution = var2substitution
        self.confidence = confidence
        self.position2provenance_ids = {k: list(v) for k, v in position2provenance_ids.items()}
        self.org_document_id = org_document_id
        self.doi = doi
        self.document_collection = document_collection
        self.document_classes = document_classes

    def to_dict(self):
        return dict(t="doc", docid=self.document_id, title=self.title, authors=self.authors,
                    journals=self.journals, year=self.publication_year, prov=self.position2provenance_ids,
                    month=self.publication_month, org_document_id=self.org_document_id, doi=self.doi,
                    collection=self.document_collection)

    def get_result_size(self):
        return 1

    def __eq__(self, other):
        if not isinstance(other, QueryDocumentResult):
            return False
        if self.document_id != other.document_id:
            return False
        for k, v in self.var2substitution.items():
            if k not in other.var2substitution:
                return False
            v_o = other.var2substitution[k]
            if v.entity_id != v_o.entity_id or v.entity_type != v_o.entity_type:
                return False
        return True


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
        return dict(t="doc_l", r=result_dict, s=self.get_result_size())

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])

    def set_slice(self, end_pos):
        self.results = self.results[:end_pos]


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
        return dict(t="agg", s=self.get_result_size(), v_n=self.variable_names,
                    sub=self._serialize_var_substitution(), r=result_dict)

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])

    def _sort_results_by_year(self, year_sort_desc):
        self.results.sort(key=lambda x: (x.publication_year, x.publication_month), reverse=year_sort_desc)


class QueryResultAggregateList(QueryResultBase):
    """
    Represents a list of aggegrations
    """

    def __init__(self):
        self.results = []
        self.count_substitutions = 0

    def add_query_result(self, result: QueryResultAggregate):
        self.results.append(result)
        self.count_substitutions += 1

    def to_dict(self):
        result_dict = [r.to_dict() for r in self.results]
        return dict(t="agg_l", r=result_dict, s=self.get_result_size(), no_subs=self.count_substitutions)

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])

    def set_slice(self, start_pos, end_pos):
        if start_pos < len(self.results):
            if end_pos <= len(self.results):
                self.results = self.results[start_pos:end_pos]
            else:
                self.results = self.results[start_pos:end_pos]
