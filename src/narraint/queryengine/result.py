from narrant.entity.drugbank2mesh import DrugBank2MeSHMapper
from narrant.entity.entityresolver import EntityResolver
from narrant.preprocessing.enttypes import CHEMICAL, DISEASE, DOSAGE_FORM, DRUG, METHOD, \
    LAB_METHOD
from narrant.entity.meshontology import MeSHOntology


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
            # Convert MeSH Tree Numbers to MeSH Descriptors
            if self.entity_type in [CHEMICAL, DISEASE, DOSAGE_FORM, METHOD, LAB_METHOD] \
                    and not self.entity_id.startswith('MESH:'):
                mesh_ontology = MeSHOntology.instance()
                try:
                    self.entity_id = 'MESH:{}'.format(mesh_ontology.get_descriptor_for_tree_no(self.entity_id)[0])
                except KeyError:
                    pass

            # Translate Chemicals to DrugBank ids if possible
            if self.entity_type in [CHEMICAL]:
                mapper = DrugBank2MeSHMapper.instance()
                mapping = mapper.get_dbid_for_meshid(self.entity_id)
                if mapping:
                    self.entity_id = mapping
                    # Todo: not the best solution :/ Think about excipient and drugbank chemicals
                    self.entity_type = DRUG

            ent_name = entity_resolver.get_name_for_var_ent_id(self.entity_id, self.entity_type,
                                                               resolve_gene_by_id=False)
        except KeyError:
            ent_name = self.entity_str
        if ent_name == self.entity_id:
            ent_name = self.entity_str
        return ent_name

    def __str__(self):
        return '{} ("{}" "{}")'.format(self.entity_name, self.entity_id, self.entity_type)

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return dict(n=self.entity_name, s=self.entity_str, id=self.entity_id,
                    t=self.entity_type)


class QueryFactExplanation:
    """
    Represents a Fact explanation
    contains the sentence in which the fact is included, the cleaned predicate detected by OpenIE and the canonicalized
    version of the predicate
    """

    def __init__(self, position, sentence, predicate, predicate_canonicalized, subject_str, object_str, predication_id):
        self.position = position
        self.sentence = sentence
        self.predicate = predicate
        self.predicate_canonicalized = predicate_canonicalized
        self.subject_str = subject_str
        self.object_str = object_str
        self.predication_ids = {predication_id}

    def __str__(self):
        return '{} [{}, "{}" -> "{}", {}]'.format(self.sentence, self.subject_str, self.predicate,
                                                  self.predicate_canonicalized, self.object_str)

    def to_dict(self):
        return dict(s=self.sentence, p=self.predicate,
                    p_c=self.predicate_canonicalized,
                    s_str=self.subject_str, o_str=self.object_str, pos=self.position,
                    ids=','.join([str(i) for i in self.predication_ids]))


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
        return dict(t="doc", docid=self.document_id, title=self.title, e=e_dict)

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
        return dict(t="agg_l", r=result_dict, s=self.get_result_size())

    def get_result_size(self):
        return sum([r.get_result_size() for r in self.results])

