#!/bin/bash


# Generate Drug Overviews
python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_drug_keywords.py
python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_covid_keywords.py

# Update Schema Graph for Keyword2Graph translation
python ~/NarrativeIntelligence/src/narraint/keywords2graph/schema_support_graph.py


# Rebuild the retrieval indexes
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py --low-memory
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --low-memory