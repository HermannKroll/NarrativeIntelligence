
POLLUX_DOC="/home/kroll/workingdir/pollux/pollux_docs.json"
POLLUX_DOC_ENTITIES="/home/kroll/workingdir/pollux/pollux_docs_with_entities.json"
POLLUX_OPENIE6_EXTRACATIONS_TEST="/home/kroll/workingdir/pollux/extractions/openie6_benchmark.tsv"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC $POLLUX_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 NF POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC $POLLUX_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. OpenIE6 NF POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC $POLLUX_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 NF POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC_ENTITIES $POLLUX_OPENIE6_EXTRACATIONS_TEST  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 EF POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC_ENTITIES $POLLUX_OPENIE6_EXTRACATIONS_TEST  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. OpenIE6 EF POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC_ENTITIES $POLLUX_OPENIE6_EXTRACATIONS_TEST  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 EF POLLUX: ${DIFF}s"




WIKIPEDIA_DOC="/home/kroll/workingdir/wikipedia/wikipedia_scientists.json"
WIKIPEDIA_DOC_ENTITIES="/home/kroll/workingdir/wikipedia/wikipedia_scientists_entities.json"
WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST="/home/kroll/workingdir/wikipedia/extractions/openie6_benchmark.tsv"

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 NF Wikipedia: ${DIFF}s"


# START=$(date +%s.%N)
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
# END=$(date +%s.%N)
# DIFF=$(echo "$END - $START" | bc)
# echo "2. OpenIE6 NF Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 NF Wikipedia: ${DIFF}s"



#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC_ENTITIES $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 EF Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC_ENTITIES $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. OpenIE6 EF Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC_ENTITIES $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 EF Wikipedia: ${DIFF}s"




PUBMED_SAMPLE="/home/kroll/workingdir/pubmed/pubmed_10k_sample.json"
PUBMED_OPENIE6_TEMP="/home/kroll/workingdir/pubmed/openie6_performance.tsv"



START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  --no_entity_filter 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "1. OpenIE6 NF PubMed: ${DIFF}s"


START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  --no_entity_filter 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "2. OpenIE6 NF PubMed: ${DIFF}s"


START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  --no_entity_filter 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "3. OpenIE6 NF PubMed: ${DIFF}s"



START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "1. OpenIE6 EF PubMed: ${DIFF}s"


START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "2. OpenIE6 EF PubMed: ${DIFF}s"


START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "3. OpenIE6 EF PubMed: ${DIFF}s"
