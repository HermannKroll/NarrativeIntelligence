eval "$(conda shell.bash hook)"
conda activate narraint
export PYTHONPATH="/home/pubpharm/NarrativeIntelligence/src/:/home/pubpharm/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/home/pubpharm/NarrativeIntelligence/lib/KGExtractionToolbox/src/"

# Remove old cache
echo "Deleting old cache backup directory"
rm -rf ~/NarrativeIntelligence/cache_old
# Create a backup of the current cache
echo "Backup cache directory"
mv ~/NarrativeIntelligence/cache ~/NarrativeIntelligence/cache_old

# Execute common queries
echo "Executing common queries again"
python3 ~/NarrativeIntelligence/src/narraint/frontend/ui/execute_common_queries.py
