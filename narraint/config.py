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

# UMLS
UMLS_DATA = os.path.join(DATA_DIR, "umls/MRCONSO.RRF.gz")
UMLS_MAPPING = os.path.join(DATA_DIR, "umls/mapping.json")

# SemMed
SEMMEDDB_CONFIG = os.path.join(CONFIG_DIR, 'semmed.json')

# MeSH Ontology Index File
MESH_ONTOLOGY_INDEX_FILE = os.path.join(TMP_DIR, "mesh_ontology_index.pkl")

# MESH
MESH_DESCRIPTORS_FILE = os.path.join(DATA_DIR, "desc2020.xml")
MESH_SUPPLEMENTARY_FILE = os.path.join(DATA_DIR, "supp2020.xml")
MESH_ID_TO_HEADING_INDEX_FILE = os.path.join(TMP_DIR, 'desc2020_id2heading.pkl')
MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE = os.path.join(TMP_DIR, 'supp2020_id2heading.pkl')

# GENE
GENE_FILE = os.path.join(DATA_DIR, 'gene_info_2020.gz')
GENE_INDEX_FILE = os.path.join(TMP_DIR, 'gene_info_2020_id2name.pkl')

# Taxonomy Names 2020
TAXONOMY_FILE = os.path.join(RESOURCE_DIR, 'taxonomy_names_2020.gz')
TAXONOMY_INDEX_FILE = os.path.join(TMP_DIR, 'taxonomy_name_index.pkl')

# Preprocessing
PREPROCESS_CONFIG = os.path.join(CONFIG_DIR, 'preprocess.json')

# NLP
NLP_DATA = os.path.join(DATA_DIR, "stanfordnlp_resources")

# Graph
GRAPH_GV = os.path.join(DATA_DIR, "graph/graph.gv")

# OpenIE
OPENIE_CONFIG = os.path.join(CONFIG_DIR, "openie.json")

# Backend for Tagging
BACKEND_CONFIG = os.path.join(CONFIG_DIR, "backend.json")

# DosageForm Tagger
DOSAGE_FORM_TAGGER_INDEX_CACHE = os.path.join(TMP_DIR, "df_index_cache.pkl")
DOSAGE_ADDITIONAL_DESCS = os.path.join(RESOURCE_DIR, "df_additional_descs.txt")
DOSAGE_ADDITIONAL_DESCS_TERMS = os.path.join(RESOURCE_DIR, "df_additional_descs_terms.txt")
DOSAGE_FID_DESCS = os.path.join(RESOURCE_DIR, "df_fid_descriptors.txt")
