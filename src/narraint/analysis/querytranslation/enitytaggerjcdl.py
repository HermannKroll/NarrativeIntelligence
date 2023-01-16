import gzip
import logging
import os.path
import pickle
import string
from collections import defaultdict
from itertools import islice

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.entitylinking.tagging.vocabulary import Vocabulary
from kgextractiontoolbox.progress import Progress
from narraint.atc.atc_tree import ATCTree
from narraint.backend.models import JCDLInvertedEntityIndex
from narraint.config import TMP_DIR
from narrant.config import MESH_DESCRIPTORS_FILE, GENE_FILE, DISEASE_TAGGER_VOCAB_DIRECTORY
from narrant.entity.entityresolver import EntityResolver, get_gene_ids
from narrant.entity.meshontology import MeSHOntology
from narrant.mesh.data import MeSHDB
from narrant.preprocessing.enttypes import DISEASE, ALL, PLANT_FAMILY_GENUS, GENE, TARGET, SPECIES, DOSAGE_FORM, \
    VACCINE, EXCIPIENT, DRUG, CHEMICAL
from narrant.vocabularies.chemical_vocabulary import ChemicalVocabulary
from narrant.vocabularies.dosageform_vocabulary import DosageFormVocabulary
from narrant.vocabularies.drug_vocabulary import DrugVocabulary
from narrant.vocabularies.excipient_vocabulary import ExcipientVocabulary
from narrant.vocabularies.plant_family_genus import PlantFamilyGenusVocabulary
from narrant.vocabularies.vaccine_vocabulary import VaccineVocabulary

ENTITY_TAGGING_INDEX_JCDL = os.path.join(TMP_DIR, "entity_tagger_index_jcdl.pkl")


class EntityTaggerJCDL:
    """
    EntityTaggerJCDL converts a string to an entity
    Performs a simple dictionary-based lookup and returns the corresponding entity
    Builds upon the EntityResolver and computes reverse indexes,
    e.g. Gene_ID -> Gene_Name is converted to Gene_Name -> Gene_ID
    """
    __instance = None

    @staticmethod
    def instance(load_index=True):
        if EntityTaggerJCDL.__instance is None:
            EntityTaggerJCDL(load_index=load_index)
        return EntityTaggerJCDL.__instance

    def __init__(self, load_index=True):
        self.autocompletion = None
        self.relevant_entity_ids = set()
        if EntityTaggerJCDL.__instance is not None:
            raise Exception('This class is a singleton - use EntityTaggerJCDL.instance()')
        else:
            logging.info('Initialize EntityTaggerJCDL...')
            self.term2entity = defaultdict(set)
            self.entity_type2entities = {}
            self.mesh_ontology = MeSHOntology.instance()
            if load_index:
                self._load_index()
            EntityTaggerJCDL.__instance = self

    def _load_index(self, index_path=ENTITY_TAGGING_INDEX_JCDL):
        logging.info(f'Loading entity tagging index from {index_path}')
        with open(index_path, 'rb') as f:
            self.term2entity, self.entity_type2entities = pickle.load(f)
        logging.info(f'Index load ({len(self.term2entity)} different terms)')

    def store_index(self, index_path=ENTITY_TAGGING_INDEX_JCDL):
        logging.info('Computing entity tagging index...')

        logging.info('Querying relevant entity ids...')
        session = Session.get()
        count = session.query(JCDLInvertedEntityIndex).count()
        progress = Progress(total=count, print_every=1000, text="Retrieving entities...")
        progress.start_time()
        for idx, r in enumerate(session.query(JCDLInvertedEntityIndex.entity_id).yield_per(1000)):
            progress.print_progress(idx)
            self.relevant_entity_ids.add(r[0])
        progress.done()
        logging.info(f'Load {len(self.relevant_entity_ids)} relevant entity ids from JCDL entity index...')

        self._create_reverse_index()
        logging.info(f'Storing index to {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump((self.term2entity, self.entity_type2entities), f)
        logging.info('Index stored')

    def _add_term_to_index(self, term: str, entity_id: str, entity_type: str):
        if entity_id in self.relevant_entity_ids:
            term_lower = term.strip().lower().replace('-', ' ').replace('+', ' ')
            self.term2entity[term_lower].add(entity_id)

            if entity_type:
                if entity_type not in self.entity_type2entities:
                    self.entity_type2entities[entity_type] = set()
                self.entity_type2entities[entity_type].add(entity_id)

    def _create_reverse_index(self):
        self.term2entity = defaultdict(set)
        resolver = EntityResolver.instance()
        for e_term, e_id in resolver.species.get_reverse_index().items():
            self._add_term_to_index(e_term, e_id, SPECIES)

        # add all entity types
        for entity_type in ALL:
            self._add_term_to_index(entity_type, entity_type, entity_type)
        # add special rules
        self._add_term_to_index(TARGET, GENE, GENE)
        self._add_term_to_index(TARGET, GENE, TARGET)
        self._add_term_to_index("PlantGenus", PLANT_FAMILY_GENUS, PLANT_FAMILY_GENUS)
        self._add_term_to_index("Plant Genus", PLANT_FAMILY_GENUS, PLANT_FAMILY_GENUS)
        self._add_term_to_index("PlantGenera", PLANT_FAMILY_GENUS, PLANT_FAMILY_GENUS)
        self._add_term_to_index("Plant Genera", PLANT_FAMILY_GENUS, PLANT_FAMILY_GENUS)

        self._add_chembl_atc_classes()
        self._add_chembl_drugs()
        self._add_chembl_chemicals()
        self._add_additional_diseases()
        self._add_gene_terms()
        self._add_excipient_terms()
        self._add_mesh_tags()
        self._add_fid_dosageform_terms()
        self._add_vaccine_terms()
        self._add_plant_families()
        logging.info('{} different terms map to entities'.format(len(self.term2entity)))

    def _add_additional_diseases(self):
        logging.info('Adding additional diseases')
        vocab_path = os.path.join(DISEASE_TAGGER_VOCAB_DIRECTORY, "vocabulary.tsv")
        dis_vocab = Vocabulary(vocab_path)
        dis_vocab.load_vocab(expand_terms=False)

        for term, ent_ids in dis_vocab.vocabularies[DISEASE].items():
            for ent_id in ent_ids:
                self._add_term_to_index(term, ent_id, DISEASE)

    def _add_gene_terms(self, gene_input=GENE_FILE):
        gene_ids_in_db = get_gene_ids(Session.get())
        logging.info('Reading gene input file: {}'.format(gene_input))
        with gzip.open(gene_input, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                gene_id = int(components[1])
                if gene_id in gene_ids_in_db:
                    gene_symbol = components[2].strip().lower()
                    synonyms = components[4]
                    description = components[8].strip().lower()
                    self._add_term_to_index(gene_symbol, gene_symbol, GENE)
                    self._add_term_to_index(gene_symbol, gene_symbol, TARGET)
                    self._add_term_to_index(description, gene_symbol, GENE)
                    self._add_term_to_index(description, gene_symbol, TARGET)
                    for synonym in synonyms.split('|'):
                        self._add_term_to_index(synonym, gene_symbol, GENE)
                        self._add_term_to_index(synonym, gene_symbol, TARGET)
        logging.info('Gene terms added')

    def _add_fid_dosageform_terms(self):
        """
        Add the additional dosage form terms to the internal translation dict
        :return: None
        """
        for term, df_ids in DosageFormVocabulary.create_dosage_form_vocabulary(expand_by_s_and_e=False).items():
            for df_id in df_ids:
                self._add_term_to_index(term, df_id, DOSAGE_FORM)

    def _add_vaccine_terms(self):
        """
        Add all vaccine entries
        :return:
        """
        for term, vaccine_ids in VaccineVocabulary.create_vaccine_vocabulary(expand_by_s_and_e=False).items():
            for vaccine_id in vaccine_ids:
                self._add_term_to_index(term, vaccine_id, VACCINE)

    def _add_excipient_terms(self):
        """
        Add all excipient terms to the internal dict
        :return:
        """
        for excipient_name in ExcipientVocabulary.read_excipients_names(expand_terms=False):
            self._add_term_to_index(excipient_name, excipient_name.capitalize(), EXCIPIENT)

    def _add_plant_families(self):
        """
        Add all plant family names
        :return:
        """
        for family_name in PlantFamilyGenusVocabulary.read_plant_family_genus_vocabulary(expand_terms=False):
            self._add_term_to_index(family_name, family_name.capitalize(), PLANT_FAMILY_GENUS)

    def _add_mesh_tags(self, mesh_file=MESH_DESCRIPTORS_FILE):
        logging.info('Reading mesh file: {}'.format(mesh_file))
        meshdb = MeSHDB.instance()
        meshdb.load_xml(mesh_file)
        for desc in meshdb.get_all_descs():
            mesh_id, mesh_head = f'MESH:{desc.unique_id}', desc.heading
            try:
                for ent_type in self.mesh_ontology.get_entity_types_for_descriptor(desc.unique_id):
                    self._add_term_to_index(mesh_head, mesh_id, ent_type)
                    for term in desc.terms:
                        self._add_term_to_index(term.string, mesh_id, ent_type)
            except KeyError:
                self._add_term_to_index(mesh_head, mesh_id, None)
                for term in desc.terms:
                    self._add_term_to_index(term.string, mesh_id, None)

    def _add_chembl_drugs(self):
        logging.info('Adding ChEMBL drugs...')
        drug_terms2dbid = DrugVocabulary.create_drug_vocabulary_from_chembl(ignore_excipient_terms=False,
                                                                            ignore_drugbank_chemicals=False,
                                                                            expand_terms=False)
        for term, chids in drug_terms2dbid.items():
            for chid in chids:
                self._add_term_to_index(term, chid, DRUG)

    def _add_chembl_atc_classes(self):
        """
        Adds a mapping from atc 4 level names to all ChEMBL ids that are in that class
        :return: None
        """
        # read also atc classes
        atc_tree: ATCTree = ATCTree.instance()
        for atc_class, atc_class_name in atc_tree.atcclass2name.items():
            name = atc_class_name.strip().lower()
            self._add_term_to_index(name, atc_class.upper(), DRUG)

    def _add_chembl_chemicals(self):
        logging.info('Adding ChEMBL chemicals...')
        drug_terms2dbid = ChemicalVocabulary.create_chembl_chemical_vocabulary()
        for term, chids in drug_terms2dbid.items():
            for chid in chids:
                self._add_term_to_index(term, chid, CHEMICAL)

    def tag_entity(self, term: str, expand_search_by_prefix=False):
        """
        Tags an entity by given a string
        :param term: the entity term
        :param expand_search_by_prefix: If true, all known terms that have the given term as a prefix are used to search
        :return: a set of entities entity_id
        """
        t_low = term.lower().strip().replace('-', ' ').replace('+', ' ')
        entities = set()
        if expand_search_by_prefix:
            if not self.autocompletion:
                from narraint.frontend.entity import autocompletion
                self.autocompletion = autocompletion.AutocompletionUtil.instance()
            expanded_terms = self.autocompletion.find_entities_starting_with(t_low, retrieve_k=1000)
            logging.debug(f'Expanding term "{t_low}" with: {expanded_terms}')
            for term in expanded_terms:
                entities.update(self.tag_entity(term, expand_search_by_prefix=False))

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

    entity_tagger = EntityTaggerJCDL.instance(load_index=False)
    entity_tagger.store_index()


if __name__ == "__main__":
    main()
