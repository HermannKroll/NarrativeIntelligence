import itertools
import sys
from datetime import datetime
from typing import List
from lxml import etree

from narraint.mesh.data import BaseNode, Concept, Term
from narraint.mesh.utils import get_text, get_datetime, get_list

MESH_SUPP_QUERY_DESCRIPTOR_RECORD = "/SupplementalRecordSet/SupplementalRecord"
MESH_SUPP_QUERY_DESCRIPTOR_BY_ID = "/SupplementalRecordSet/SupplementalRecord/SupplementalRecordUI[text()='{}']/parent::*"

MESH_SUPP_QUERY_DESCRIPTOR_BY_HEADING_CONTAINS = "/SupplementalRecordSet/SupplementalRecord/SupplementalRecordName" \
                                       "/String[contains(text(),'{}')]/parent::*/parent::*"
MESH_SUPP_QUERY_DESCRIPTOR_BY_HEADING_EXACT = "/SupplementalRecordSet/SupplementalRecord/SupplementalRecordName" \
                                    "/String[text()='{}']/parent::*/parent::*"
MESH_SUPP_QUERY_DESCRIPTOR_BY_TERM = "/SupplementalRecordSet/SupplementalRecord/ConceptList/Concept/TermList/Term" \
                           "/String[text()='{}']/parent::*/parent::*/parent::*/parent::*/parent::*"


class SupplementaryRecordMappedTo(BaseNode):
    _attrs = dict(
        _name=(get_text, "DescriptorReferredTo/DescriptorName/String", True),
        _unique_id=(get_text, "DescriptorReferredTo/DescriptorUI", True),

    )

    @property
    def name(self):
        return getattr(self, "_name")

    @property
    def unique_id(self) -> str:
        return getattr(self, "_unique_id")

    def __str__(self):
        return "<SupplementaryHeadingMappedTo {} ({})>".format(self.name, self.unique_id)

    def __repr__(self):
        return "<SupplementaryHeadingMappedTo {} ({})>".format(self.name, self.unique_id)


class SupplementaryRecord(BaseNode):
    _attrs = dict(
        date_created=(get_datetime, "DateCreated"),
        date_revised=(get_datetime, "DateRevised"),
        concept_list=(get_list, "ConceptList", Concept.from_element, True),
        _heading_mapped_to=(get_list, "HeadingMappedToList", SupplementaryRecordMappedTo.from_element),
        _name=(get_text, "SupplementalRecordName/String", True),
        _note=(get_text, "Note"),
        _unique_id=(get_text, "SupplementalRecordUI", True),
        term_list=(get_list, "TermList", Term.from_element, True),
    )

    @property
    def name(self):
        return getattr(self, "_name")

    @property
    def unique_id(self) -> str:
        return getattr(self, "_unique_id")

    @property
    def note(self) -> str:
        return getattr(self, "_note")

    @property
    def concepts(self) -> List[Concept]:
        return getattr(self, "concept_list")

    @property
    def headings_mapped_to(self) -> List[SupplementaryRecordMappedTo]:
        return getattr(self, "_heading_mapped_to")

    @property
    def terms(self) -> List[Term]:
        if not hasattr(self, "_terms"):
            terms = list(itertools.chain.from_iterable(c.term_list for c in self.concept_list))
            setattr(self, "_terms", terms)
        return getattr(self, "_terms")

    def __str__(self):
        return "<SupplementaryRecord {} ({})>".format(self.name, self.unique_id)

    def __repr__(self):
        return "<SupplementaryRecord {} ({})>".format(self.name, self.unique_id)


class MeSHDBSupplementary:
    """
    Class is a Singleton for the MeSH Supplementary database.
    You can load a descriptor file and query descriptors with the functions

    - record_by_id
    - record_by_tree_number
    - records_by_name
    - records_by_term

    Use the instance() method to get a MeSHSupplementary instance.
    """
    __instance = None

    @staticmethod
    def instance():
        if MeSHDBSupplementary.__instance is None:
            MeSHDBSupplementary()
        return MeSHDBSupplementary.__instance

    def __init__(self):
        self.tree = None
        self._desc_by_id = dict()
        self._desc_by_name = dict()
        if MeSHDBSupplementary.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MeSHDBSupplementary.__instance = self

    def load_xml(self, filename, prefetch_all=False, verbose=False):
        if not self._desc_by_id:
            start = datetime.now()
            with open(filename) as f:
                self.tree = etree.parse(f)
            end = datetime.now()
            if verbose:
                print("XML loaded in {}".format(end - start))
            if prefetch_all:
                start = datetime.now()
                self.prefetch_all(verbose)
                end = datetime.now()
                if verbose:
                    print("All descriptors loaded in {}".format(end - start))

    def prefetch_all(self, verbose=False):
        records = self.tree.xpath(MESH_SUPP_QUERY_DESCRIPTOR_RECORD)
        total = len(records)
        last = 0
        if verbose:
            sys.stdout.write("Indexing ...")
            sys.stdout.flush()
        for idx, record in enumerate(records):
            desc = SupplementaryRecord.from_element(record)
            self.add_record(desc)
            if verbose and int((idx + 1.0) / total * 100.0) > last:
                last = int((idx + 1.0) / total * 100.0)
                sys.stdout.write("\rIndexing ... {} %".format(last))
                sys.stdout.flush()
        if verbose:
            sys.stdout.write("\rIndexing ... done\n")
            sys.stdout.flush()

    def get_all_records(self) -> List[SupplementaryRecord]:
        descs = []
        records = self.tree.xpath(MESH_SUPP_QUERY_DESCRIPTOR_RECORD)
        for idx, record in enumerate(records):
            desc = SupplementaryRecord.from_element(record)
            descs.append(desc)
        return descs

    def add_record(self, record):
        self._desc_by_id[record.unique_id] = record
        self._desc_by_name[record.name] = record

    def record_by_id(self, unique_id) -> SupplementaryRecord:
        if unique_id not in self._desc_by_id:
            query = MESH_SUPP_QUERY_DESCRIPTOR_BY_ID.format(unique_id)
            desc_rec = self.tree.xpath(query)
            if desc_rec:
                desc = SupplementaryRecord.from_element(desc_rec[0])
                self.add_record(desc)
            else:
                raise ValueError("Record {} not found.".format(unique_id))
        return self._desc_by_id[unique_id]

    def records_by_term(self, term) -> List[SupplementaryRecord]:
        query = MESH_SUPP_QUERY_DESCRIPTOR_BY_TERM.format(term)
        records = self.tree.xpath(query)
        desc_list = [SupplementaryRecord.from_element(record) for record in records]
        # Add to cache
        for desc in desc_list:
            if desc.unique_id not in self._desc_by_id:
                self.add_record(desc)
        return desc_list

    def records_by_name(self, name, match_exact=True, search_terms=True) -> List[SupplementaryRecord]:
        if match_exact and name in self._desc_by_name:
            return [self._desc_by_name[name]]
        if match_exact:
            query = MESH_SUPP_QUERY_DESCRIPTOR_BY_HEADING_EXACT.format(name)
        else:
            query = MESH_SUPP_QUERY_DESCRIPTOR_BY_HEADING_CONTAINS.format(name)
        records = self.tree.xpath(query)
        desc_list = [SupplementaryRecord.from_element(record) for record in records]
        # Add to cache
        for desc in desc_list:
            if desc.unique_id not in self._desc_by_id:
                self.add_record(desc)
        # Search by terms
        if not desc_list and search_terms:
            desc_list = self.records_by_term(name)
        # Return
        return desc_list

