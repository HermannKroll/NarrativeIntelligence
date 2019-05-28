"""
XML Documentation: https://www.nlm.nih.gov/mesh/xml_data_elements.html
"""
import itertools

from lxml import etree

from mesh.utils import get_datetime, get_text, get_attr, get_list, get_element_text

QUERY_DESCRIPTOR_RECORD = "/DescriptorRecordSet/DescriptorRecord"
QUERY_DESCRIPTOR_BY_ID = "/DescriptorRecordSet/DescriptorRecord/DescriptorUI[text()='{}']/parent::*"
QUERY_DESCRIPTOR_BY_TREE_NUMBER = "/DescriptorRecordSet/DescriptorRecord/TreeNumberList" \
                                  "/TreeNumber[text()='{}']/parent::*/parent::*"
QUERY_DESCRIPTOR_BY_HEADING_CONTAINS = "/DescriptorRecordSet/DescriptorRecord/DescriptorName" \
                                       "/String[contains(text(),'{}')]/parent::*/parent::*"
QUERY_DESCRIPTOR_BY_TERM = "/DescriptorRecordSet/DescriptorRecord/ConceptList/Concept/TermList/Term" \
                           "/String[text()='{}']/parent::*/parent::*/parent::*/parent::*/parent::*"


# noinspection PyTypeChecker,PyUnresolvedReferences
class MeSHDB:
    """
    Class is a Singleton for the MeSH database. You can load a descriptor file and query descriptors with the functions

    - desc_by_id
    - desc_by_tree_number
    - descs_by_name
    - descs_by_term

    Use the instance() method to get a MeSHDB instance.
    """
    __instance = None

    @staticmethod
    def instance():
        if MeSHDB.__instance is None:
            MeSHDB()
        return MeSHDB.__instance

    def __init__(self):
        self.tree = None
        self._desc_by_id = dict()
        self._desc_by_tree_number = dict()
        if MeSHDB.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MeSHDB.__instance = self

    def load_xml(self, filename, prefetch_all=False, verbose=False):
        with open(filename) as f:
            self.tree = etree.parse(f)
        if verbose:
            print("XML loaded.")
        if prefetch_all:
            self.prefetch_all()
            if verbose:
                print("All descriptors loaded.")

    def prefetch_all(self):
        records = self.tree.xpath(QUERY_DESCRIPTOR_RECORD)
        for record in records:
            desc = Descriptor.from_element(record)
            self._desc_by_id[desc.unique_id] = desc

    def add_desc(self, desc_obj):
        self._desc_by_id[desc_obj.unique_id] = desc_obj
        self._desc_by_tree_number[desc_obj.tree_number_list[0]] = desc_obj

    def desc_by_id(self, unique_id):
        if unique_id not in self._desc_by_id:
            query = QUERY_DESCRIPTOR_BY_ID.format(unique_id)
            desc_rec = self.tree.xpath(query)
            if desc_rec:
                desc = Descriptor.from_element(desc_rec[0])
                self.add_desc(desc)
            else:
                raise ValueError("Descriptor not found.")
        return self._desc_by_id[unique_id]

    def desc_by_tree_number(self, tree_number):
        if tree_number not in self._desc_by_tree_number:
            query = QUERY_DESCRIPTOR_BY_TREE_NUMBER.format(tree_number)
            desc_rec = self.tree.xpath(query)
            if desc_rec:
                desc = Descriptor.from_element(desc_rec[0])
                self.add_desc(desc)
            else:
                raise ValueError("Descriptor not found.")
        return self._desc_by_tree_number[tree_number]

    def descs_by_term(self, term):
        query = QUERY_DESCRIPTOR_BY_TERM.format(term)
        records = self.tree.xpath(query)
        desc_list = [Descriptor.from_element(record) for record in records]
        # Add to cache
        for desc in desc_list:
            if desc.unique_id not in self._desc_by_id.keys():
                self.add_desc(desc)
        return desc_list

    def descs_by_name(self, name):
        # TODO: Option: Match exactly
        # TODO: Option: Dont search for terms
        query = QUERY_DESCRIPTOR_BY_HEADING_CONTAINS.format(name)
        records = self.tree.xpath(query)
        desc_list = [Descriptor.from_element(record) for record in records]
        # Add to cache
        for desc in desc_list:
            if desc.unique_id not in self._desc_by_id.keys():
                self.add_desc(desc)
        # Search by terms
        if not desc_list:
            desc_list = self.descs_by_term(name)
        # Return
        return desc_list


class BaseNode:
    _attrs = dict()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.__class__._attrs.keys():
                setattr(self, key, value)

    @classmethod
    def from_element(cls, record, *args):
        kwargs = dict()
        for key, (func, *func_args) in cls._attrs.items():
            kwargs[key] = func(record, *func_args)
        return cls(**kwargs)

    def print(self, print_unset=False):
        for key in self._attrs.keys():
            if getattr(self, key, None) or print_unset:
                print(f"{key}={getattr(self, key)}")

    @property
    def attrs(self):
        return tuple(self._attrs.keys())


class Term(BaseNode):
    _attrs = dict(
        abbreviation=(get_text, "Abbreviation"),
        concept_preferred_term_yn=(get_attr, "ConceptPreferredTermYN"),
        date_created=(get_datetime, "DateCreated"),
        entry_version=(get_text, "EntryVersion"),
        is_permuted_term_yn=(get_attr, "IsPermutedTermYN"),
        lexical_tag=(get_attr, "LexicalTag"),
        record_preferred_term_yn=(get_attr, "RecordPreferredTermYN"),
        sort_version=(get_text, "SortVersion"),
        string=(get_text, "String", True),
        term_note=(get_text, "TermNote"),
        term_ui=(get_text, "TermUI", True),
        thesaurus_id_list=(get_list, "ThesaurusIDList", get_element_text),
    )

    def __str__(self):
        return "<Term {}>".format(getattr(self, "string"))

    def __repr__(self):
        return "<Term {} at {}>".format(getattr(self, "string"), id(self))


# TODO: Add reference to concept
class ConceptRelation(BaseNode):
    _attrs = dict(
        concept1ui=(get_text, "Concept1UI"),
        concept2ui=(get_text, "Concept2UI"),
        relation_name=(get_attr, "RelationName"),
    )


class Concept(BaseNode):
    _attrs = dict(
        cas_type_1_name=(get_text, "CASN1Name"),
        concept_relation_list=(get_list, "ConceptRelationList", ConceptRelation.from_element),
        concept_ui=(get_text, "ConceptUI", True),
        name=(get_text, "ConceptName/String", True),
        preferred_concept_yn=(get_attr, "PreferredConceptYN"),
        registry_number=(get_text, "RegistryNumber"),
        related_registry_number_list=(get_list, "RelatedRegistryNumberList", get_element_text),
        scope_note=(get_text, "ScopeNote"),
        term_list=(get_list, "TermList", Term.from_element, True),
        translators_english_scope_note=(get_text, "TranslatorsEnglishScopeNote"),
        translators_scope_note=(get_text, "TranslatorsScopeNote"),
    )

    def __str__(self):
        return "<Concept {}>".format(getattr(self, "name"))

    def __repr__(self):
        return "<Concept {} at {}>".format(getattr(self, "name"), id(self))


# TODO: Add reference to descriptor
class PharmacologicalAction(BaseNode):
    pass


# TODO: Add reference to descriptor
class SeeRelatedDescriptor(BaseNode):
    pass


# noinspection PyUnresolvedReferences
class Descriptor(BaseNode):
    _attrs = dict(
        annotation=(get_text, "Annotation"),
        concept_list=(get_list, "ConceptList", Concept.from_element, True),
        consider_also=(get_text, "ConsiderAlso"),
        date_created=(get_datetime, "DateCreated"),
        date_revised=(get_datetime, "DateRevised"),
        date_established=(get_datetime, "DateEstablished", True),
        descriptor_class=(get_attr, "DescriptorClass"),
        heading=(get_text, "DescriptorName/String", True),
        history_note=(get_text, "HistoryNote"),
        nlm_classification_number=(get_text, "NLMClassificationNumber"),
        mesh_note=(get_text, "PublicMeSHNote"),
        online_note=(get_text, "OnlineNote"),
        pharmacological_action_list=(get_list, "PharmacologicalActionList", PharmacologicalAction.from_element),
        previous_indexing_list=(get_list, "PreviousIndexingList", get_element_text),
        scr_class=(get_attr, "SCRClass"),
        see_related_list=(get_list, "SeeRelatedList", SeeRelatedDescriptor.from_element),
        tree_number_list=(get_list, "TreeNumberList", get_element_text, True),
        unique_id=(get_text, "DescriptorUI", True),
    )

    @property
    def tree_number(self):
        return getattr(self, "tree_number_list")[0]

    @property
    def parent(self):
        parent = ".".join(self.tree_number.split(".")[:-1])
        if parent:
            return MeSHDB.instance().desc_by_tree_number(parent)
        else:
            return None

    @property
    def lineage(self):
        if not hasattr(self, "_lineage"):
            parent_lineage = self.parent.lineage if self.parent else []
            lineage = parent_lineage + [self]
            setattr(self, "_lineage", lineage)
        return getattr(self, "_lineage")

    def get_common_lineage(self, other):
        lin1 = self.lineage
        lin2 = other.lineage
        return [x for x, y in zip(lin1, lin2) if x == y]

    @property
    def terms(self):
        if not hasattr(self, "_terms"):
            terms = list(itertools.chain.from_iterable(c.term_list for c in self.concept_list))
            setattr(self, "_terms", terms)
        return getattr(self, "_terms")

    def __str__(self):
        return "<Descriptor {}>".format(getattr(self, "heading"))

    def __repr__(self):
        return "<Descriptor {} at {}>".format(getattr(self, "heading"), id(self))
