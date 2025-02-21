import gzip
import logging
import os.path
from collections import defaultdict
from datetime import datetime
from itertools import islice

import marisa_trie

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.entitylinking.tagging.vocabulary import Vocabulary
from kgextractiontoolbox.progress import print_progress_with_eta
from narraint.backend.models import Tag
from narrant.atc.atc_tree import ATCTree
from narrant.config import MESH_DESCRIPTORS_FILE, GENE_FILE, DISEASE_TAGGER_VOCAB_DIRECTORY, MESH_SUPPLEMENTARY_FILE
from narrant.entity.entityresolver import EntityResolver, get_gene_ids
from narrant.entity.meshontology import MeSHOntology
from narrant.entitylinking.enttypes import GENE, SPECIES, DOSAGE_FORM, DRUG, EXCIPIENT, PLANT_FAMILY_GENUS, CHEMICAL, \
    VACCINE, DISEASE, TARGET, ORGANISM, CELLLINE
from narrant.mesh.data import MeSHDB
from narrant.mesh.supplementary import MeSHDBSupplementary
from narrant.vocabularies.cellline_vocabulary import CellLineVocabulary
from narrant.vocabularies.chemical_vocabulary import ChemicalVocabulary
from narrant.vocabularies.dosageform_vocabulary import DosageFormVocabulary
from narrant.vocabularies.drug_vocabulary import DrugVocabulary
from narrant.vocabularies.excipient_vocabulary import ExcipientVocabulary
from narrant.vocabularies.organism_vocabulary import OrganismVocabulary
from narrant.vocabularies.plant_family_genus import PlantFamilyGenusVocabulary
from narrant.vocabularies.target_vocabulary import TargetVocabulary
from narrant.vocabularies.vaccine_vocabulary import VaccineVocabulary


class EntityIndexBase:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self):
        self.expand_by_subclasses = True
        self.mesh_ontology = MeSHOntology()

    def _add_term(self, term, entity_id: str, entity_type: str, entity_class: str = None):
        raise NotImplementedError

    def _create_index(self):

        resolver = EntityResolver()
        for e_term, e_id in resolver.species.get_reverse_index().items():
            self._add_term(e_term, e_id, SPECIES)

        self._add_additional_diseases()
        self._add_gene_terms()
        self._add_excipient_terms()
        self._add_mesh_tags()
        self._add_mesh_supplements()
        self._add_chembl_atc_classes()
        self._add_chembl_drugs()
        self._add_chembl_chemicals()
        self._add_fid_dosageform_terms()
        self._add_vaccine_terms()
        self._add_plant_families()
        # Targets are deactivated at the moment
        # self._add_chembl_targets()
        self._add_chembl_organisms()
        self._add_celllines()

    def _add_additional_diseases(self):
        logging.info('Adding additional diseases')
        vocab_path = os.path.join(DISEASE_TAGGER_VOCAB_DIRECTORY, "vocabulary.tsv")
        dis_vocab = Vocabulary(vocab_path)
        dis_vocab.load_vocab(expand_terms=False)

        for term, ent_ids in dis_vocab.vocabularies[DISEASE].items():
            for ent_id in ent_ids:
                self._add_term(term, ent_id, DISEASE)

    def _add_gene_terms(self, gene_input=GENE_FILE):
        gene_ids_in_db = get_gene_ids(Session.get())
        logging.info('Reading gene input file: {}'.format(gene_input))
        with gzip.open(gene_input, 'rt') as f:
            for line in islice(f, 1, None):
                components = str(line).strip().split('\t')
                gene_id = int(components[1])
                if gene_id in gene_ids_in_db:
                    gene_symbol = components[2].strip().lower()
                    synonyms = components[4]
                    description = components[8].strip()
                    self._add_term(gene_symbol, gene_symbol, GENE)
                    self._add_term(description, gene_symbol, GENE)
                    for synonym in synonyms.split('|'):
                        self._add_term(synonym, gene_symbol, GENE)
        logging.info('Gene terms added')

    def _add_fid_dosageform_terms(self):
        """
        Add the additional dosage form terms to the internal translation dict
        :return: None
        """
        for term, df_ids in DosageFormVocabulary.create_dosage_form_vocabulary(expand_by_s_and_e=False).items():
            for df_id in df_ids:
                self._add_term(term, df_id, DOSAGE_FORM)

    def _add_vaccine_terms(self):
        """
        Add all vaccine entries
        :return:
        """
        for term, vaccine_ids in VaccineVocabulary.create_vaccine_vocabulary(expand_by_s_and_e=False).items():
            for vaccine_id in vaccine_ids:
                self._add_term(term, vaccine_id, VACCINE)

    def _add_excipient_terms(self):
        """
        Add all excipient terms to the internal dict
        :return:
        """
        for term, ex_ids in ExcipientVocabulary.create_excipient_vocabulary(expand_terms=False).items():
            for ex_id in ex_ids:
                self._add_term(term, ex_id, EXCIPIENT)

    def _add_plant_families(self):
        """
        Add all plant family names
        :return:
        """
        for family_name in PlantFamilyGenusVocabulary.read_plant_family_genus_vocabulary(expand_terms=False):
            self._add_term(family_name, family_name.capitalize(), PLANT_FAMILY_GENUS)

    def _add_mesh_tags(self, mesh_file=MESH_DESCRIPTORS_FILE):
        logging.info('Reading mesh file: {}'.format(mesh_file))
        meshdb = MeSHDB()
        meshdb.load_xml(mesh_file)
        mesh_mappings = defaultdict(set)
        for desc in meshdb.get_all_descs():
            mesh_id, mesh_head = desc.unique_id, desc.heading
            mesh_mappings[mesh_id].add(mesh_head)
            for term in desc.terms:
                mesh_mappings[mesh_id].add(term.string)

        # Should we expand mesh descriptors by their subdescriptors
        if self.expand_by_subclasses:
            logging.info('Expanding MeSH Descriptors by their sub descriptors...')
            logging.info('Computing Trie for fast lookup...')
            start_time = datetime.now()

            trie_entries = set()
            for idx, mesh_id in enumerate(mesh_mappings):
                print_progress_with_eta("computing trie entries", idx, len(mesh_mappings), start_time, print_every_k=10)
                try:
                    tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(mesh_id)
                    for tn in tree_nos:
                        trie_entries.add(f'{tn.lower()}:{mesh_id}')
                except KeyError:
                    continue
            mesh_trie = marisa_trie.Trie(trie_entries)

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
                                    term = mesh_term
                                    self._add_term(term, f'MESH:{mesh_id}', ent_type)
                                    for sub_d in sub_descs:
                                        self._add_term(term, f'MESH:{sub_d.split(":")[1]}', ent_type)
                        except KeyError:
                            continue
                except KeyError:
                    continue
        else:
            # no expansion we can just add them
            logging.info('Do NOT expand MeSH Descriptors by their sub descriptors...')
            start_time = datetime.now()
            for idx, (mesh_id, mesh_terms) in enumerate(mesh_mappings.items()):
                print_progress_with_eta("adding mesh terms", idx, len(mesh_mappings), start_time, print_every_k=10)
                try:
                    tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(mesh_id)
                    for tn in tree_nos:
                        # find the given entity type for the tree number
                        try:
                            for ent_type in MeSHOntology.tree_number_to_entity_type(tn):
                                for mesh_term in mesh_terms:
                                    term = mesh_term
                                    self._add_term(term, f'MESH:{mesh_id}', ent_type)
                        except KeyError:
                            continue
                except KeyError:
                    continue

    def _add_mesh_supplements(self, mesh_supplement_file=MESH_SUPPLEMENTARY_FILE):
        # All MeSH supplements are Diseases in our database
        # However, loading all supplements into the index will be too large
        # That is why we query all tagged MeSH supplements first and use them to build the index
        logging.info(f'Reading MeSH supplement file: {mesh_supplement_file}')
        mesh_supp = MeSHDBSupplementary()
        mesh_supp.load_xml(filename=mesh_supplement_file)

        logging.info('Query all MeSH supplements from Tag table...')
        session = Session.get()
        q = session.query(Tag.ent_id.distinct()).filter(Tag.ent_id.like('MESH:C%'))
        used_supplements_records = set()
        for r in q:
            used_supplements_records.add(r[0])

        logging.info(f'{len(used_supplements_records)} supplement records found in DB. Extracting terms...')
        for record in used_supplements_records:
            r_id = record.replace('MESH:', '')
            try:
                supp_record = mesh_supp.record_by_id(r_id)
                self._add_term(supp_record.name, record, DISEASE)
                for term in supp_record.terms:
                    term_str = term.string
                    self._add_term(term_str, record, DISEASE)
            except ValueError:
                pass

    def _add_chembl_drugs(self):
        logging.info('Adding ChEMBL drugs...')
        drug_terms2dbid = DrugVocabulary.create_drug_vocabulary_from_chembl(ignore_excipient_terms=False,
                                                                            ignore_drugbank_chemicals=False,
                                                                            expand_terms=False)
        for term, chids in drug_terms2dbid.items():
            for chid in chids:
                self._add_term(term, chid, DRUG)

    def _add_chembl_atc_classes(self):
        """
        Adds a mapping from atc 4 level names to all ChEMBL ids that are in that class
        :return: None
        """
        # read also atc classes
        if self.expand_by_subclasses:
            logging.info('Adding ATC tree information...')
            atc_tree: ATCTree = ATCTree()
            for atc_class_name, chembl_ids in atc_tree.atcclassname2chembl.items():
                for chid in chembl_ids:
                    self._add_term(atc_class_name, chid, DRUG, entity_class=atc_class_name)
        else:
            logging.info('Skipping atc tree information')

    def _add_chembl_chemicals(self):
        logging.info('Adding ChEMBL chemicals...')
        drug_terms2dbid = ChemicalVocabulary.create_chembl_chemical_vocabulary(expand_terms=False)
        for term, chids in drug_terms2dbid.items():
            for chid in chids:
                self._add_term(term, chid, CHEMICAL)

    def _add_chembl_targets(self):
        logging.info('Adding ChEMBL targets...')
        terms2id = TargetVocabulary.create_target_vocabulary(expand_by_s_and_e=False)
        for term, chids in terms2id.items():
            for chid in chids:
                self._add_term(term, chid, TARGET)

    def _add_chembl_organisms(self):
        logging.info('Adding ChEMBL organism...')
        terms2id = OrganismVocabulary.create_organism_vocabulary(expand_by_s_and_e=False)
        for term, chids in terms2id.items():
            for chid in chids:
                self._add_term(term, chid, ORGANISM)

    def _add_celllines(self):
        logging.info('Adding Cell Lines...')
        terms2id = CellLineVocabulary.create_cell_line_vocabulary(expand_by_s_and_e=False)
        for term, chids in terms2id.items():
            for chid in chids:
                self._add_term(term, chid, CELLLINE)
