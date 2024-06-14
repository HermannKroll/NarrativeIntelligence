#!/bin/bash

source ~/NarrativeIntelligence/scripts/.mailenv
SUBJECT="Narrative Service update error"

if [ -t 1 ] ; then
eval "$(conda shell.bash hook)"
conda activate narrant
fi

export PYTHONPATH="/root/NarrativeIntelligence/src/:/root/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/root/NarrativeIntelligence/lib/KGExtractionToolbox/src/"

# Generate Drug Overviews
python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_drug_keywords.py 2> /root/ns_update_every_6_month_err.log
if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_every_6_month_err.log
    exit -1
fi

python3 ~/NarrativeIntelligence/src/narraint/keywords/generate_covid_keywords.py 2> /root/ns_update_every_6_month_err.log
if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_every_6_month_err.log
    exit -1
fi


# Update Schema Graph for Keyword2Graph translation
python ~/NarrativeIntelligence/src/narraint/keywords2graph/schema_support_graph.py 2> /root/ns_update_every_6_month_err.log
if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_every_6_month_err.log
    exit -1
fi


# Rebuild the retrieval indexes
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py 2> /root/ns_update_every_6_month_err.log
if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_every_6_month_err.log
    exit -1
fi

python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --low-memory 2> /root/ns_update_every_6_month_err.log
if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_every_6_month_err.log
    exit -1
fi


echo "Narrative Every-6-Month Update done" | mailx -s "Narrative Service  Every-6-Month Update done" "$ADDRESS" -r "$SENDER"
