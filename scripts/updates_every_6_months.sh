#!/bin/bash


# Generate Drug Overviews
python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_drug_keywords.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_covid_keywords.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi


# Update Schema Graph for Keyword2Graph translation
python ~/NarrativeIntelligence/src/narraint/keywords2graph/schema_support_graph.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi


# Rebuild the retrieval indexes
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --low-memory
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi
