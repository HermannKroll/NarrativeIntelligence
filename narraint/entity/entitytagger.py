import logging
from collections import defaultdict

import pickle

from narraint.config import DOSAGE_FID_DESCS, DOSAGE_ADDITIONAL_DESCS_TERMS, MESH_DESCRIPTORS_FILE, \
    MESH_SUPPLEMENTARY_FILE, ENTITY_TAGGING_INDEX
from narraint.entity.entity import Entity
from narraint.entity.entityresolver import EntityResolver
from narraint.entity.enttypes import GENE, SPECIES, DOSAGE_FORM, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, PLANT_FAMILY
from narraint.entity.meshontology import MeSHOntology
from narraint.mesh.data import MeSHDB
from narraint.mesh.supplementary import MeSHDBSupplementary
from narraint.preprocessing.tagging.vocabularies import ExcipientVocabulary, PlantFamilyVocabulary, DrugTaggerVocabulary


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
    __instance = None

    @staticmethod
    def instance():
        if EntityTagger.__instance is None:
            EntityTagger()
        return EntityTagger.__instance

    def __init__(self):
        if EntityTagger.__instance is not None:
            raise Exception('This class is a singleton - use EntityTagger.instance()')
        else:
            logging.info('Initialize EntityTagger...')
            self.resolver = EntityResolver.instance()
            self.term2entity = defaultdict(set)
            self.mesh_ontology = MeSHOntology.instance()
            self._load_index()
            EntityTagger.__instance = self

    def _load_index(self, index_path=ENTITY_TAGGING_INDEX):
        logging.info(f'Loading entity tagging index from {index_path}')
        with open(index_path, 'rb') as f:
            self.term2entity = pickle.load(f)
        logging.info('Index load')

    def store_index(self, index_path=ENTITY_TAGGING_INDEX):
        logging.info('Computing entity tagging index...')
        self._create_reverse_index()
        logging.info(f'Storing index to {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump(self.term2entity, f)
        logging.info('Index stored')

    def _create_reverse_index(self):
        self.term2entity = defaultdict(set)
        for e_term, e_id in self.resolver.gene.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()].add(Entity(e_id, GENE))
        for e_term, e_id in self.resolver.species.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()].add(Entity(e_id, SPECIES))

        self._add_excipient_terms()
        self._add_mesh_tags()
        self._add_drugbank_tags()
        self._add_fid_dosageform_terms()
        self._add_plant_families()
        logging.info('{} different terms map to entities'.format(len(self.term2entity)))

    def _add_fid_dosageform_terms(self):
        """
        Add the additional dosage form terms to the internal translation dict
        :return: None
        """
        for df_id, terms in DosageFormTaggerVocabulary.get_dosage_form_vocabulary_terms().items():
            for t in terms:
                self.term2entity[t.lower()].add(Entity(df_id, DOSAGE_FORM))

    def _add_excipient_terms(self):
        """
        Add all excipient terms to the internal dict
        :return:
        """
        for excipient_name in ExcipientVocabulary.read_excipients_names(expand_terms_by_e_and_s=False):
            self.term2entity[excipient_name.lower()].add(Entity(excipient_name.capitalize(), EXCIPIENT))

    def _add_plant_families(self):
        """
        Add all plant family names
        :return:
        """
        for family_name in PlantFamilyVocabulary.read_plant_family_vocabulary(expand_terms_by_e=False):
            self.term2entity[family_name.strip().lower()].add(Entity(family_name.capitalize(), PLANT_FAMILY))

    def _add_mesh_tags(self, mesh_file=MESH_DESCRIPTORS_FILE, mesh_supp_file=MESH_SUPPLEMENTARY_FILE):
        logging.info('Reading mesh file: {}'.format(mesh_file))
        meshdb = MeSHDB.instance()
        meshdb.load_xml(mesh_file)
        mesh_mappings = []
        for desc in meshdb.get_all_descs():
            mesh_id, mesh_head = desc.unique_id, desc.heading
            mesh_mappings.append((mesh_id, mesh_head))
            for term in desc.terms:
                mesh_mappings.append((mesh_id, term.string))

        logging.info('Mesh read ({} entries)'.format(len(mesh_mappings)))
        for mesh_id, mesh_term in mesh_mappings:
            term = mesh_term.lower()
            try:
                tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(mesh_id)
                for tn in tree_nos:
                    self.term2entity[term].add(Entity(tn, 'MESH_ONTOLOGY'))
            except KeyError:
                self.term2entity[term].add(Entity('MESH:{}'.format(mesh_id), 'MESH'))

        logging.info('Reading mesh supplementary file: {}'.format(mesh_supp_file))
        mesh_supplementary = MeSHDBSupplementary.instance()
        for desc in mesh_supplementary.get_all_descs(mesh_supp_file):
            desc_id = f'MESH:{desc.unique_id}'
            term_l = desc.heading.lower()
            self.term2entity[term_l].add(Entity(desc_id, 'MESH'))
        logging.info('MeSH Terms added')

    def _add_drugbank_tags(self):
        logging.info('Adding DrugBank terms...')
        drug_terms2dbid = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(ignore_excipient_terms=False,
                                                                                      ignore_drugbank_chemicals=False,
                                                                                      expand_term_with_e_and_s=False)
        for term, dbids in drug_terms2dbid.items():
            for dbid in dbids:
                self.term2entity[term.lower()].add(Entity(dbid, 'Drug'))
        logging.info('DrugBank terms added')

    def tag_entity(self, term: str):
        """
        Tags an entity by given a string
        :param term: the entity term
        :return: an entity as (entity_id, entity_type)
        """
        t_low = term.lower().strip()
        if t_low not in self.term2entity:
            if t_low[-1] == 's':
                t_low_n = t_low[:-2]
            else:
                t_low_n = f'{t_low}s'
            if t_low_n not in self.term2entity:
                raise KeyError('Does not know an entity for term: {}'.format(t_low))
            else:
                t_low = t_low_n
        return self.term2entity[t_low]



def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    entity_tagger = EntityTagger.instance()
    entity_tagger.store_index()
    print(entity_tagger.tag_entity('simvastatin'))
    print(entity_tagger.tag_entity('metformin'))
    print(entity_tagger.tag_entity('metformine'))
    print(entity_tagger.tag_entity('Dimethylbiguanid'))
    print(entity_tagger.tag_entity('dimethylbiguanid'))

if __name__ == "__main__":
    main()
