#!/bin/bash


# Generate Drug Overviews
python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_drug_keywords.py
python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_covid_keywords.py

# Update Schema Graph for Keyword2Graph translation
python ~/NarrativeIntelligence/src/narraint/keywords2graph/schema_support_graph.py