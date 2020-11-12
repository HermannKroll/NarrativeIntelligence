import logging
from collections import defaultdict

from narraint.config import DOSAGE_FID_DESCS, DOSAGE_ADDITIONAL_DESCS_TERMS
from narraint.entity.entity import Entity
from narraint.entity.entityresolver import EntityResolver
from narraint.entity.enttypes import GENE, SPECIES, DOSAGE_FORM, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, PLANT_FAMILY
from narraint.entity.meshontology import MeSHOntology
from narraint.preprocessing.tagging.vocabularies import ExcipientVocabulary, PlantFamilyVocabulary


class DosageFormTaggerVocabulary:

    def __init__(self):
        pass

    @staticmethod
    def get_dosage_form_vocabulary_terms():
        """
        Get all self-designed vocabulary terms for DosageForms
        :return: a dict mapping the dosage form id to a set of terms
        """
        dfid2terms = defaultdict(set)
        with open(DOSAGE_FID_DESCS, 'rt') as f:
            for line in f:
                df_id, df_head, *rest = line.strip().split('\t')
                dfid2terms[df_id].add(df_head)
                if rest:
                    rest = rest[0]
                    if ';' in rest:
                        terms = rest.split(';')
                        for t in terms:
                            dfid2terms[df_id].add(t.strip())
                    else:
                        dfid2terms[df_id].add(rest.strip())

        with open(DOSAGE_ADDITIONAL_DESCS_TERMS, 'rt') as f:
            for line in f:
                df_id, synonyms = line.strip().split('\t')
                if ';' in synonyms:
                    terms = synonyms.split(';')
                    for t in terms:
                        dfid2terms[df_id].add(t.strip())
                else:
                    dfid2terms[df_id].add(synonyms.strip())
        return dfid2terms


class EntityTagger:
    """
    EntityTagger converts a string to an entity
    Performs a simple dictionary-based lookup and returns the corresponding entity
    Builds upon the EntityResolver and computes reverse indexes,
    e.g. Gene_ID -> Gene_Name is converted to Gene_Name -> Gene_ID
    """
    def __init__(self):
        self.resolver = EntityResolver.instance()
        self.term2entity = defaultdict(list)
        self.mesh_ontology = MeSHOntology.instance()
        self._create_reverse_index()

    def _add_to_reverse_index(self, items, e_type, id_prefix=''):
        for e_id, e_term in items:
            term = e_term.lower().strip()
            self.term2entity[term].append(Entity(id_prefix+e_id, e_type))

    def _create_mesh_ontology_index(self, items):
        for desc_id, heading in items:
            term = heading.lower().strip()
            try:
                tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(desc_id)
                for tn in tree_nos:
                    self.term2entity[term].append(Entity(tn, 'MESH_ONTOLOGY'))
            except KeyError:
                self.term2entity[term].append(Entity('MESH:{}'.format(desc_id), 'MESH'))

    def _create_reverse_index(self):
        for e_term, e_id in self.resolver.gene.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()].append(Entity(e_id, GENE))
        for e_term, e_id in self.resolver.species.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()].append(Entity(e_id, SPECIES))
        for e_id, e_term in self.resolver.drugbank.dbid2name.items():
            self.term2entity[e_term.strip().lower()].append(Entity(e_id, DRUG))

        self._add_to_reverse_index(self.resolver.mesh.supplement_desc2heading.items(), 'MESH', id_prefix='MESH:')
        self._create_mesh_ontology_index(self.resolver.mesh.desc2heading.items())
        self._add_fid_dosageform_terms()
        self._add_excipient_terms()
        self._add_drugbank_chemicals()
        self._add_plant_families()
        logging.info('{} different terms map to entities'.format(len(self.term2entity)))

    def _add_fid_dosageform_terms(self):
        """
        Add the additional dosage form terms to the internal translation dict
        :return: None
        """
        for df_id, terms in DosageFormTaggerVocabulary.get_dosage_form_vocabulary_terms().items():
            for t in terms:
                self.term2entity[t.lower()].append(Entity(df_id, DOSAGE_FORM))

    def _add_excipient_terms(self):
        """
        Add all excipient terms to the internal dict
        :return:
        """
        for e_id, e_term in self.resolver.drugbank.dbid2name.items():
            self.term2entity[e_term.strip().lower()].append(Entity(e_id, EXCIPIENT))

        for excipient_name in ExcipientVocabulary.read_excipients_names():
            self.term2entity[excipient_name.lower()].append(Entity(excipient_name.capitalize(), EXCIPIENT))

    def _add_drugbank_chemicals(self):
        """
        Add all drugbank chmeical terms to the internal dict
        :return:
        """
        for e_id, e_term in self.resolver.drugbank.dbid2name.items():
            self.term2entity[e_term.strip().lower()].append(Entity(e_id, DRUGBANK_CHEMICAL))

    def _add_plant_families(self):
        """
        Add all plant family names
        :return:
        """
        for family_name in PlantFamilyVocabulary.read_plant_family_vocabulary(expand_terms_by_e=False):
            self.term2entity[family_name.strip().lower()].append(Entity(family_name.capitalize(), PLANT_FAMILY))
        
    def tag_entity(self, term: str):
        """
        Tags an entity by given a string
        :param term: the entity term
        :return: an entity as (entity_id, entity_type)
        """
        t_low = term.lower().strip()
        if t_low not in self.term2entity:
            raise KeyError('Does not know an entity for term: {}'.format(t_low))
        return self.term2entity[t_low]

