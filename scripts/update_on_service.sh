
# Remove old cache
rm -rf ~/NarrativeIntelligence/cache_old
# Create a backup of the current cache
mv ~/NarrativeIntelligence/cache ~/NarrativeIntelligence/cache_old

# Execute common queries
python3 ~/NarrativeIntelligence/src/narraint/frontend/ui/execute_common_queries.py
