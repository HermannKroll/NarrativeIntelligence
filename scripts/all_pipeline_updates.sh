#!/bin/bash

source .mailenv
SUBJECT="Narrative Service update error"

conda activate narrant
export PYTHONPATH="/root/NarrativeIntelligence/src/:/root/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/root/NarrativeIntelligence/lib/KGExtractionToolbox/src/"

bash ~/NarrativeAnnotation/scripts/process_zbmed_for_service.sh 2> /root/ns_update_err.log

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_err.log
    exit -1
fi


bash ~/NarrativeAnnotation/scripts/process_pubmed_updates_for_service.sh 2> /root/ns_update_err.log

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_err.log
    exit -1
fi


bash ~/NarrativeAnnotation/scripts/process_clean_extractions.sh 2> /root/ns_update_err.log

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_err.log
    exit -1
fi


bash ~/NarrativeIntelligence/scripts/update_service_data.sh 2> /root/ns_update_err.log

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < /root/ns_update_err.log
    exit -1
fi