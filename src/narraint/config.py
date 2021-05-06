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

if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

if not os.path.isdir(TMP_DIR_TAGGER):
    os.makedirs(TMP_DIR_TAGGER)

# UMLS
UMLS_DATA = os.path.join(DATA_DIR, "umls/MRCONSO.RRF.gz")
UMLS_MAPPING = os.path.join(DATA_DIR, "umls/mapping.json")

# SemMed
SEMMEDDB_CONFIG = os.path.join(CONFIG_DIR, 'semmed.json')


# Backend for Tagging
BACKEND_CONFIG = os.path.join(CONFIG_DIR, "backend.json")

# Entity Tagging index
ENTITY_TAGGING_INDEX = os.path.join(TMP_DIR, 'entity_tagging_index.pkl')

# Autocompletion Index
AUTOCOMPLETION_TMP_INDEX = os.path.join(TMP_DIR, 'autocompletion.pkl')

# NLP Config
NLP_CONFIG = os.path.join(CONFIG_DIR, 'nlp.json')

