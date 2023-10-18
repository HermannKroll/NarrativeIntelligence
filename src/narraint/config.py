"""
This module contains constants which point to important directories.
"""
import os

GIT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

DATA_DIR = os.path.join(GIT_ROOT_DIR, "data")
RESOURCE_DIR = os.path.join(GIT_ROOT_DIR, "resources")
CONFIG_DIR = os.path.join(GIT_ROOT_DIR, "config")
LOG_DIR = os.path.join(GIT_ROOT_DIR, "logs")
TMP_DIR = os.path.join(GIT_ROOT_DIR, "tmp")
TMP_DIR_TAGGER = os.path.join(TMP_DIR, 'tagger')
CACHE_DIR = os.path.join(GIT_ROOT_DIR, 'cache')
CODE_DIR = os.path.join(GIT_ROOT_DIR, 'narraint')
REPORT_DIR = os.path.join(GIT_ROOT_DIR, 'reports')

QUERY_YIELD_PER_K = 1000000
BULK_INSERT_AFTER_K = 100000

if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

if not os.path.isdir(TMP_DIR_TAGGER):
    os.makedirs(TMP_DIR_TAGGER)

# Backend for Tagging
BACKEND_CONFIG = os.path.join(CONFIG_DIR, "backend.json")

# CHEMBL ATC Tree
CHEMBL_ATC_TREE_FILE = os.path.join(RESOURCE_DIR, "chembl_atc_tree.json")

# MeSH Disease Tree
MESH_DISEASE_TREE_JSON = os.path.join(RESOURCE_DIR, "mesh_disease_tree.json")

# Entity Tagging index
ENTITY_TAGGING_INDEX = os.path.join(TMP_DIR, 'entity_tagging_index.pkl')

# Entity Explainer Index
ENTITY_EXPLAINER_INDEX = os.path.join(TMP_DIR, 'entity_explainer_index.pkl')

# Autocompletion Index
AUTOCOMPLETION_TMP_INDEX = os.path.join(TMP_DIR, 'autocompletion.pkl')

# Drug keyword extraction stopword list
DRUG_KEYWORD_STOPWORD_LIST = os.path.join(RESOURCE_DIR, 'stopwords_drug_keywords.txt')
