import gzip
import gzip
import logging
import os.path
import pickle
import string
from collections import defaultdict
from datetime import datetime
from itertools import islice

import datrie

from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import Tag
from narraint.config import ENTITY_TAGGING_INDEX
from narrant.config import MESH_DESCRIPTORS_FILE, GENE_FILE, DISEASE_TAGGER_VOCAB_DIRECTORY
from narrant.entity.entity import Entity
from narrant.entity.entityresolver import EntityResolver
from narrant.entity.meshontology import MeSHOntology
from narrant.mesh.data import MeSHDB
from narrant.preprocessing.enttypes import GENE, SPECIES, DOSAGE_FORM, DRUG, EXCIPIENT, PLANT_FAMILY_GENUS, CHEMICAL, \
    VACCINE, DISEASE
from narrant.preprocessing.tagging.vocabulary import Vocabulary
from narrant.progress import print_progress_with_eta
from narrant.vocabularies.chemical_vocabulary import ChemicalVocabulary
from narrant.vocabularies.drug_vocabulary import DrugVocabulary
from narrant.vocabularies.excipient_vocabulary import ExcipientVocabulary
from narrant.vocabularies.plant_family_genus import PlantFamilyGenusVocabulary


class EntityTagger:
    """
    EntityTagger converts a string to an entity
    Performs a simple dictionary-based lookup and returns the corresponding entity
    Builds upon the EntityResolver and computes reverse indexes,
    e.g. Gene_ID -> Gene_Name is converted to Gene_Name -> Gene_ID
    """
    __instance = None

    @staticmethod
    def instance(load_index=True):
        if EntityTagger.__instance is None:
            EntityTagger(load_index=load_index)
        return EntityTagger.__instance

    def __init__(self, load_index=True):
        if EntityTagger.__instance is not None:
            raise Exception('This class is a singleton - use EntityTagger.instance()')
        else:
            logging.info('Initialize EntityTagger...')
            self.term2entity = defaultdict(set)
            self.mesh_ontology = MeSHOntology.instance()
            if load_index:
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
        resolver = EntityResolver.instance()
        for e_term, e_id in resolver.species.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()].add(Entity(e_id, SPECIES))

        self._add_additional_diseases()
        self._add_gene_terms()
        self._add_excipient_terms()
        self._add_mesh_tags()
        self._add_chembl_atc_classes()
        self._add_chembl_drugs()
        self._add_chembl_chemicals()
        self._add_fid_dosageform_terms(resolver=resolver)
        self._add_vaccine_terms(resolver=resolver)
        self._add_plant_families()
        logging.info('{} different terms map to entities'.format(len(self.term2entity)))

    def _add_additional_diseases(self):
        logging.info('Adding additional diseases')
        vocab_path = os.path.join(DISEASE_TAGGER_VOCAB_DIRECTORY, "vocabulary.tsv")
        dis_vocab = Vocabulary(vocab_path)
        dis_vocab.load_vocab(expand_terms=False)

        for term, ent_ids in dis_vocab.vocabularies[DISEASE].items():
            for ent_id in ent_ids:
                self.term2entity[term.lower().strip()].add(Entity(ent_id, DISEASE))

    def _add_gene_terms(self, gene_input=GENE_FILE):
        gene_ids_in_db = Tag.get_gene_ids(SessionExtended.get())
        logging.info('Reading gene input file: {}'.format(gene_input))
        with gzip.open(gene_input, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                gene_id = int(components[1])
                if gene_id in gene_ids_in_db:
                    gene_symbol = components[2].strip().lower()
                    synonyms = components[4]
                    description = components[8].strip().lower()
                    self.term2entity[gene_symbol].add(Entity(gene_symbol, GENE))
                    self.term2entity[description].add(Entity(gene_symbol, GENE))
                    for synonym in synonyms.split('|'):
                        self.term2entity[synonym.strip().lower()].add(Entity(gene_symbol, GENE))
        logging.info('Gene terms added')

    def _add_fid_dosageform_terms(self, resolver: EntityResolver):
        """
        Add the additional dosage form terms to the internal translation dict
        :return: None
        """
        for term, df_ids in resolver.dosageform.dosageform_vocabulary.vocabularies[DOSAGE_FORM].items():
            for df_id in df_ids:
                self.term2entity[term].add(Entity(df_id, DOSAGE_FORM))

    def _add_vaccine_terms(self, resolver: EntityResolver):
        """
        Add all vaccine entries
        :return:
        """
        for term, vaccine_ids in resolver.vaccine.vaccine_vocab.vocabularies[VACCINE].items():
            for vaccine_id in vaccine_ids:
                self.term2entity[term].add(Entity(vaccine_id, VACCINE))

    def _add_excipient_terms(self):
        """
        Add all excipient terms to the internal dict
        :return:
        """
        for excipient_name in ExcipientVocabulary.read_excipients_names(expand_terms=False):
            self.term2entity[excipient_name.lower()].add(Entity(excipient_name.capitalize(), EXCIPIENT))

    def _add_plant_families(self):
        """
        Add all plant family names
        :return:
        """
        for family_name in PlantFamilyGenusVocabulary.read_plant_family_genus_vocabulary(expand_terms=False):
            self.term2entity[family_name.strip().lower()].add(Entity(family_name.capitalize(), PLANT_FAMILY_GENUS))

    def _add_mesh_tags(self, mesh_file=MESH_DESCRIPTORS_FILE):
        logging.info('Reading mesh file: {}'.format(mesh_file))
        meshdb = MeSHDB.instance()
        meshdb.load_xml(mesh_file)
        mesh_mappings = defaultdict(set)
        for desc in meshdb.get_all_descs():
            mesh_id, mesh_head = desc.unique_id, desc.heading
            mesh_mappings[mesh_id].add(mesh_head)
            for term in desc.terms:
                mesh_mappings[mesh_id].add(term.string)

        logging.info('Computing Trie for fast lookup...')
        start_time = datetime.now()
        mesh_trie = datrie.Trie(string.printable)
        for idx, mesh_id in enumerate(mesh_mappings):
            print_progress_with_eta("computing trie", idx, len(mesh_mappings), start_time, print_every_k=10)
            try:
                tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(mesh_id)
                for tn in tree_nos:
                    tn_and_id = f'{tn.lower()}:{mesh_id}'
                    mesh_trie[tn_and_id] = tn_and_id
            except KeyError:
                continue

        logging.info('Finished')

        logging.info('Mesh read ({} entries)'.format(len(mesh_mappings)))
        start_time = datetime.now()
        for idx, (mesh_id, mesh_terms) in enumerate(mesh_mappings.items()):
            print_progress_with_eta("adding mesh terms", idx, len(mesh_mappings), start_time, print_every_k=10)
            try:
                tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(mesh_id)
                for tn in tree_nos:
                    # find the given entity type for the tree number
                    try:
                        for ent_type in MeSHOntology.tree_number_to_entity_type(tn):
                            sub_descs = mesh_trie.keys(tn.lower())
                            for mesh_term in mesh_terms:
                                term = mesh_term.lower()
                                self.term2entity[term].add(Entity(f'MESH:{mesh_id}', ent_type))
                                self.term2entity[term].update([Entity(f'MESH:{s.split(":")[1]}', ent_type)
                                                               for s in sub_descs if s != mesh_id])

                    except KeyError:
                        continue
            except KeyError:
                continue

    def _add_chembl_drugs(self):
        logging.info('Adding ChEMBL drugs...')
        drug_terms2dbid = DrugVocabulary.create_drug_vocabulary_from_chembl(ignore_excipient_terms=False,
                                                                            ignore_drugbank_chemicals=False,
                                                                            expand_terms=False)
        for term, chids in drug_terms2dbid.items():
            for chid in chids:
                self.term2entity[term.lower()].add(Entity(chid, DRUG))

    def _add_chembl_atc_classes(self):
        """
        Adds a mapping from atc 4 level names to all ChEMBL ids that are in that class
        :return: None
        """
        # read also atc classes
        atc_tree: ATCTree = ATCTree.instance()
        for atc_class_name, chembl_ids in atc_tree.atcclassname2chembl.items():
            for chid in chembl_ids:
                self.term2entity[atc_class_name].add(Entity(chid, DRUG, entity_class=atc_class_name))

    def _add_chembl_chemicals(self):
        logging.info('Adding ChEMBL chemicals...')
        drug_terms2dbid = ChemicalVocabulary.create_chembl_chemical_vocabulary()
        for term, chids in drug_terms2dbid.items():
            for chid in chids:
                self.term2entity[term.lower()].add(Entity(chid, CHEMICAL))

    def tag_entity(self, term: str):
        """
        Tags an entity by given a string
        :param term: the entity term
        :return: a list of entities (entity_id, entity_type)
        """
        t_low = term.lower().strip()
        entities = set()
        if not t_low:
            raise KeyError('Does not know an entity for empty term: {}'.format(term))
        # check direct string
        if t_low in self.term2entity:
            entities.update(self.term2entity[t_low])
        # also add plural if possible
        if t_low[-1] != 's' and f'{t_low}s' in self.term2entity:
            entities.update(self.term2entity[f'{t_low}s'])
        # check singular form
        if t_low[-1] == 's' and t_low[:-1] in self.term2entity:
            entities.update(self.term2entity[t_low[:-1]])

        if len(entities) == 0:
            raise KeyError('Does not know an entity for term: {}'.format(term))

        return entities


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    entity_tagger = EntityTagger.instance(load_index=False)
    entity_tagger.store_index()


if __name__ == "__main__":
    main()
