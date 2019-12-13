"""
This module contains constants which point to important directories.
"""
import os

GIT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

DATA_DIR = os.path.join(GIT_ROOT_DIR, "data")
CONFIG_DIR = os.path.join(GIT_ROOT_DIR, "config")
LOG_DIR = os.path.join(GIT_ROOT_DIR, "logs")
TMP_DIR = os.path.join(GIT_ROOT_DIR, "tmp")

# UMLS
UMLS_DATA = os.path.join(DATA_DIR, "umls/MRCONSO.RRF")
UMLS_MAPPING = os.path.join(DATA_DIR, "umls/mapping.json")

# SemMed
SEMMEDDB_CONFIG = os.path.join(CONFIG_DIR, 'semmed.json')

# MESH
MESH_DESCRIPTORS_FILE = os.path.join(DATA_DIR, "desc2020.xml")

# Preprocessing
PREPROCESS_CONFIG = os.path.join(CONFIG_DIR, 'preprocess.json')

# NLP
NLP_DATA = os.path.join(DATA_DIR, "stanfordnlp_resources")

# Graph
GRAPH_GV = os.path.join(DATA_DIR, "graph/graph.gv")

# OpenIE
OPENIE_CONFIG = os.path.join(CONFIG_DIR, "openie.json")

# OpenIE
BACKEND_CONFIG = os.path.join(CONFIG_DIR, "backend.json")
