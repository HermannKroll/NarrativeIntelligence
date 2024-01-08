#!/bin/bash
PREDICATION_MINIMUM_UPDATE_ID_FILE=/home/"$USER"/NarrativeIntelligence/scripts/highest_predication_id.txt
PREDICATION_MINIMUM_UPDATE_ID=$(<"$PREDICATION_MINIMUM_UPDATE_ID_FILE")

echo "Highest predication id is $PREDICATION_MINIMUM_UPDATE_ID"

# Finally compute the new metadata service table2
python3 ~/NarrativeIntelligence/src/narraint/queryengine/prepare_metadata_for_service.py

# Compute reverse indexes
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --predicate_id_minimum $PREDICATION_MINIMUM_UPDATE_ID
python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py --predicate_id_minimum $PREDICATION_MINIMUM_UPDATE_ID
# Not required at the moment
# python3 ~/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_term.py

# Export the highest known id
python3 ~/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/backend/export_highest_predication_id.py $PREDICATION_MINIMUM_UPDATE_ID_FILE

# Set DB date to now
python3 ~/NarrativeIntelligence/src/narraint/queryengine/update_database_update_date.py

# Remove old cache
rm -rf ~/NarrativeIntelligence/cache_old
# Create a backup of the current cache
mv ~/NarrativeIntelligence/cache ~/NarrativeIntelligence/cache_old

# Execute common queries
# python3 ~/NarrativeIntelligence/src/narraint/frontend/ui/execute_common_queries.py