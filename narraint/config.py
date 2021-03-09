"""
This module contains constants which point to important directories.
"""
import os


GIT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DATA_DIR = os.path.join(GIT_ROOT_DIR, "data")
RESOURCE_DIR = os.path.join(GIT_ROOT_DIR, "resources")
CONFIG_DIR = os.path.join(GIT_ROOT_DIR, "config")
LOG_DIR = os.path.join(GIT_ROOT_DIR, "logs")
TMP_DIR = os.path.join(GIT_ROOT_DIR, "tmp")
CACHE_DIR = os.path.join(GIT_ROOT_DIR, 'cache')
CODE_DIR = os.path.join(GIT_ROOT_DIR, 'narraint')

# UMLS
UMLS_DATA = os.path.join(DATA_DIR, "umls/MRCONSO.RRF.gz")
UMLS_MAPPING = os.path.join(DATA_DIR, "umls/mapping.json")

# SemMed
SEMMEDDB_CONFIG = os.path.join(CONFIG_DIR, 'semmed.json')

# MeSH Ontology Index File
MESH_ONTOLOGY_INDEX_FILE = os.path.join(TMP_DIR, "mesh_ontology_index.pkl")

# MESH
MESH_DESCRIPTORS_FILE = os.path.join(DATA_DIR, "desc2021.xml")
MESH_SUPPLEMENTARY_FILE = os.path.join(DATA_DIR, "supp2021.xml")
MESH_ID_TO_HEADING_INDEX_FILE = os.path.join(TMP_DIR, 'desc2021_id2heading.pkl')
MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE = os.path.join(TMP_DIR, 'supp2021_id2heading.pkl')

# Drugbase
DRUGBASE_XML_DUMP = os.path.join(DATA_DIR, "full_database.xml")

# GENE
GENE_FILE = os.path.join(DATA_DIR, 'gene_info_2020.gz')
GENE_INDEX_FILE = os.path.join(TMP_DIR, 'gene_info_2020_id2name.pkl')
GENE_TO_HUMAN_ID_FILE = os.path.join(TMP_DIR, 'gene_to_human_id.pkl')

# Taxonomy Names 2020
TAXONOMY_FILE = os.path.join(RESOURCE_DIR, 'taxonomy_names_2020.gz')
TAXONOMY_INDEX_FILE = os.path.join(TMP_DIR, 'taxonomy_name_index.pkl')

# DrugBank Resolver Index
DRUGBANK_ID2NAME_INDEX = os.path.join(TMP_DIR, 'drugbank_id2name.pkl')

# DrugBank to MeSH Mapping
DRUGBANK_ID_2_MESH_MAPPING_INDEX = os.path.join(TMP_DIR, 'drugbank2mesh.pkl')

# Preprocessing
PREPROCESS_CONFIG = os.path.join(CONFIG_DIR, 'preprocess.json')

# NLP
NLP_DATA = os.path.join(DATA_DIR, "stanfordnlp_resources")


# Backend for Tagging
BACKEND_CONFIG = os.path.join(CONFIG_DIR, "backend.json")

#Dict Tagger
DICT_TAGGER_BLACKLIST = os.path.join(RESOURCE_DIR, "dict_tagger_blacklist.txt")

# DosageForm Tagger
DOSAGE_FORM_TAGGER_INDEX_CACHE = os.path.join(TMP_DIR, "df_index_cache.pkl")
DOSAGE_ADDITIONAL_DESCS = os.path.join(RESOURCE_DIR, "df_additional_descs.txt")
DOSAGE_ADDITIONAL_DESCS_TERMS = os.path.join(RESOURCE_DIR, "df_additional_descs_terms.txt")
DOSAGE_FID_DESCS = os.path.join(RESOURCE_DIR, "df_fid_descriptors.txt")

#Drug Tagger
DRUG_TAGGER_INDEX_CACHE = os.path.join(TMP_DIR, "dr_index_cache.pkl")
DRUGBANK_CHEMICAL_DATABASE_FILE = os.path.join(RESOURCE_DIR, "drugbank_chemicals.txt")
DRUGBANK_CHEMICAL_INDEX_CACHE = os.path.join(TMP_DIR, "dc_index_cache.pkl")

# Excipient Tagger
EXCIPIENT_TAGGER_DATABASE_FILE = os.path.join(RESOURCE_DIR, 'excipient_database_2020.csv')
EXCIPIENT_TAGGER_DRUGBANK_EXCIPIENT_FILE = os.path.join(RESOURCE_DIR, 'drugbank_excipients.txt')
EXCIPIENT_TAGGER_INDEX_CACHE = os.path.join(TMP_DIR, "excipient_index_cache.pkl")

# Disease Tagger
DISEASE_TAGGER_DATABASE_FILE = MESH_DESCRIPTORS_FILE
DISEASE_TAGGER_INDEX_CACHE = os.path.join(TMP_DIR, 'disease_index_cache.pkl')

# MeSH SubHeadings for MEDLINE PubMed
MESH2DOC_INDEX_Pubmed = os.path.join(TMP_DIR, "pubmed_medline_index.pickle")
MESH2Doc_INDEX_PMC = os.path.join(TMP_DIR, "pmc_index.pkl")

# Plant Family Tagger
PLANT_FAMILTY_DATABASE_FILE = os.path.join(RESOURCE_DIR, 'plant_families_2020.txt')
PLANT_FAMILTY_INDEX_CACHE = os.path.join(TMP_DIR, 'pf_index_cache.pkl')

# Entity Tagging index
ENTITY_TAGGING_INDEX = os.path.join(TMP_DIR, 'entity_tagging_index.pkl')

# Autocompletion Index
AUTOCOMPLETION_TMP_INDEX = os.path.join(TMP_DIR, 'autocompletion.pkl')


# NLP Config
NLP_CONFIG = os.path.join(CONFIG_DIR, 'nlp.json')

if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR)