
PUBMED_SAMPLE="/home/kroll/workingdir/pubmed/pubmed_10k_sample.json"

# Load all documents
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/document/load_document.py $PUBMED_SAMPLE -c PubMed


PUBMED_OPENIE_EXTRACTIONS="/home/kroll/workingdir/pubmed/openie.tsv"
PUBMED_OPENIE5_EXTRACTIONS="/home/kroll/workingdir/pubmed/openie51.tsv"
PUBMED_OPENIE6_EXTRACTIONS="/home/kroll/workingdir/pubmed/openie6.tsv"

RELATION_VOCAB="/home/kroll/workingdir/pubmed/pharm_relation_vocab.json"

PATHIE_OUTPUT="/home/kroll/workingdir/pubmed/pathie.tsv"

PATHIE_OUTPUT_TEMP="/home/kroll/workingdir/pubmed/pathie_performance.tsv"
PUBMED_OPENIE6_TEMP="/home/kroll/workingdir/pubmed/openie6_performance.tsv"


# Analyze sentences
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/document/count_sentences.py $PUBMED_SAMPLE


# run CoreNLP
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie/main.py $PUBMED_SAMPLE $PUBMED_OPENIE_EXTRACTIONS  --no_entity_filter


# Load CoreNLP
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE_EXTRACTIONS -c PubMed -et OPENIE_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE_EXTRACTIONS -c PubMed -et OPENIE_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE_EXTRACTIONS -c PubMed -et OPENIE_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE_EXTRACTIONS -c PubMed -et OPENIE_SF --entity_filter only_subject_exact


# run OpenIE5.1
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie51/main.py $PUBMED_SAMPLE $PUBMED_OPENIE5_EXTRACTIONS  --no_entity_filter


# Load OpenIE5.1
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE5_EXTRACTIONS -c PubMed -et OPENIE5_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE5_EXTRACTIONS -c PubMed -et OPENIE5_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE5_EXTRACTIONS -c PubMed -et OPENIE5_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE5_EXTRACTIONS -c PubMed -et OPENIE5_SF --entity_filter only_subject_exact




# run OpenIE6
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_EXTRACTIONS  --no_entity_filter

# Load OpenIE6
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE6_EXTRACTIONS -c PubMed -et OPENIE6_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE6_EXTRACTIONS -c PubMed -et OPENIE6_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE6_EXTRACTIONS -c PubMed -et OPENIE6_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $PUBMED_OPENIE6_EXTRACTIONS -c PubMed -et OPENIE6_SF --entity_filter only_subject_exact


# PathIE with relation vocab
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pipeline.py -c PubMed -et PathIE --relation_vocab $RELATION_VOCAB --workers 10

# Canonicalize predicates
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py -c PubMed --word2vec_model /home/kroll/workingdir/BioWordVec_PubMed_MIMICIII_d200.bin --relation_vocab $RELATION_VOCAB


### Performance Monitoring

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $PUBMED_SAMPLE $PATHIE_OUTPUT_TEMP --relation_vocab $RELATION_VOCAB --workers 32 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. PathIE PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $PUBMED_SAMPLE $PATHIE_OUTPUT_TEMP --relation_vocab $RELATION_VOCAB --workers 32 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. PathIE PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $PUBMED_SAMPLE $PATHIE_OUTPUT_TEMP --relation_vocab $RELATION_VOCAB --workers 32 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. PathIE PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  --no_entity_filter 2>> /dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 NF PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  --no_entity_filter 2>> /dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. OpenIE6 NF PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  --no_entity_filter 2>> /dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 NF PubMed: ${DIFF}s"



#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  2>> /dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 EF PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  2>> /dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. OpenIE6 EF PubMed: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $PUBMED_SAMPLE $PUBMED_OPENIE6_TEMP  2>> /dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 EF PubMed: ${DIFF}s"



# canonicalize
# python3 ~/KGExtr