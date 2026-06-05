#!/bin/bash

# Finally compute the new metadata service table2
python3 ~/NarrativeIntelligence/src/narraint/queryengine/prepare_metadata_for_service.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

# Compute reverse indexes
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --newer-documents
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi

python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py --newer-documents
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi


# Update content information (help-page)
python ~/NarrativeIntelligence/src/narraint/backend/service_content.py
if [[ $? != 0 ]]; then
     echo "Previous script returned exit code != 0 -> Stopping pipeline."
     exit -1
fi
