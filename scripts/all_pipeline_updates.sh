#!/bin/bash

CUSTOMLOGPATH="/root/ns_update_err.log"

source ~/NarrativeIntelligence/scripts/.mailenv
SUBJECT="Narrative Service update error"

# load Base URL secret
# the env variable must be called BASE_URL
source ~/NarrativeIntelligence/scripts/.k10env
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi


if [ -t 1 ] ; then
eval "$(conda shell.bash hook)"
conda activate narrant
fi

export PYTHONPATH="/root/NarrativeIntelligence/src/:/root/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/root/NarrativeIntelligence/lib/KGExtractionToolbox/src/"


UPDATE_DATE_FILE="/data/FID_Pharmazie_Services/narrative_data_update/last_update_date.txt"
# first get the last DB update date
# we use an offset of 7 days to also crawl documents that have been published on the last update date (or if the update
# pipeline has not put them in time into the VZG index)
python3 ~/NarrativeIntelligence/src/narraint/backend/export_db_update_date.py $UPDATE_DATE_FILE --offset 14

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi

# This will load the date from .txt file directly into the bash variable for usage
UPDATE_DATE=$(<"$UPDATE_DATE_FILE")
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

# If you want to crawl all data from K10plus again, you can overwrite the Update Date here
## UPDATE_DATE="1900-01-01"


# This will invoke the Clinical Trials pipeline (data will be crawled from VZG index)
bash ~/NarrativeAnnotation/scripts/process_pubpharm_document_collection.sh "$BASE_URL" "GBV_WHO%20OR%20GBV_CTG" "$UPDATE_DATE" "ClinicalTrials" 2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi

# This will invoke the Patents pipeline (data will be crawled from VZG index)
bash ~/NarrativeAnnotation/scripts/process_pubpharm_document_collection.sh "$BASE_URL" "GBV_EPA" "$UPDATE_DATE" "Patents" 2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi

# This will invoke the Preprints pipeline (data will be crawled from VZG index)
bash ~/NarrativeAnnotation/scripts/process_pubpharm_document_collection.sh "$BASE_URL" "GBV_XAR%20OR%20GBV_XBI%20OR%20GBV_XCH%20OR%20GBV_XEN%20OR%20GBV_XRA%20OR%20techrXiv%20OR%20preprintsorg" "$UPDATE_DATE" "Preprints" 2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi

# As long as we have this pipeline, we shall use data from PubTator.
# PubTator provides additional entity annotations that are useful for our extraction pipeline
bash ~/NarrativeAnnotation/scripts/process_pubmed_updates_for_service.sh 2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi

# If PubTator is not available any more, we can switch to the following pipeline.
# However, make sure that old PubMed data is deleted first as IDs might not be compatible
# You can delete the collection via (you only need to do it once)
##  python3 ~/NarrativeIntelligence/src/narraint/backend/delete_collection.py PubMed --force
# This will invoke the MedLine pipeline (data will be crawled from VZG index)
##bash ~/NarrativeAnnotation/scripts/process_pubpharm_document_collection.sh "$BASE_URL" "GBV_NLM" "$UPDATE_DATE" "PubMed" 2> $CUSTOMLOGPATH

##if [[ $? != 0 ]]; then
##    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
##    exit -1
##fi


bash ~/NarrativeAnnotation/scripts/process_clean_extractions.sh 2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi


bash ~/NarrativeIntelligence/scripts/update_service_data.sh 2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi


# Set last database update date to now
python3 ~/NarrativeIntelligence/src/narraint/backend/update_database_update_date.py  2> $CUSTOMLOGPATH

if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi


echo "Narrative Update done" | mailx -s "Narrative Service Update done" "$ADDRESS" -r "$SENDER"


# Update clinical trial phases for drug overviews
python3 ~/NarrativeIntelligence/src/narraint/clinicaltrials/extract_trial_phases.py 2> $CUSTOMLOGPATH
if [[ $? != 0 ]]; then
    mailx -s "$SUBJECT" "$ADDRESS" -r "$SENDER" < $CUSTOMLOGPATH
    exit -1
fi

echo "Clinical Study Phases for Drug Overviews done" | mailx -s "Clinical Study Phases for Drug Overviews done" "$ADDRESS" -r "$SENDER"
