#!/bin/bash
PREDICATION_MINIMUM_UPDATE_ID_FILE=/home/"$USER"/db_highest_predication_id.txt
PREDICATION_MINIMUM_UPDATE_ID=$(<"$PREDICATION_MINIMUM_UPDATE_ID_FILE")

echo "Highest predication id is $PREDICATION_MINIMUM_UPDATE_ID"

# Finally compute the new metadata service table2
python3 ~/NarrativeIntelligence/src/narraint/queryengine/prepare_metadata_for_service.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

# Compute reverse indexes
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --predicate_id_minimum $PREDICATION_MINIMUM_UPDATE_ID
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py --predicate_id_minimum $PREDICATION_MINIMUM_UPDATE_ID
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

# Export the highest known id
python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/backend/export_highest_predication_id.py $PREDICATION_MINIMUM_UPDATE_ID_FILE
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

# Set DB date to now
python3 ~/NarrativeIntelligence/src/narraint/queryengine/update_database_update_date.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi
