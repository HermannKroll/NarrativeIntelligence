#python3.8 -u /home/jan/narint/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py -c scientists -d --format json /home/jan/wikiextractor/raw_docs


# python3.8 -u /home/jan/narint/src/narraint/pollux/load_wikipedia.py /home/jan/wikiextractor/extraction -c scientists -t "/home/jan/pollux_data/raw_input/Wikidata - Scientist with Wikipedia Article.tsv"
#
#

WIKIPEDIA_DOC="/home/kroll/workingdir/wikipedia/wikipedia_scientists.json"
WIKIPEDIA_DOC_ENTITIES="/home/kroll/workingdir/wikipedia/wikipedia_scientists_entities.json"
WIKIDATA_VOCAB="/home/kroll/workingdir/wikipedia/wikidata_vocab.tsv"

WIKIPEDIA_OPENIE_EXTRACATIONS="/home/kroll/workingdir/wikipedia/extractions/openie.tsv"
WIKIPEDIA_OPENIE5_EXTRACATIONS="/home/kroll/workingdir/wikipedia/extractions/openie51.tsv"
WIKIPEDIA_OPENIE6_EXTRACATIONS="/home/kroll/workingdir/wikipedia/extractions/openie6.tsv"

WIKIPEDIA_PATHIE_EXTRACATIONS_TEST="/home/kroll/workingdir/wikipedia/extractions/pathie_benchmark.tsv"
WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST="/home/kroll/workingdir/wikipedia/extractions/openie6_benchmark.tsv"

RELATION_VOCAB_SMALL="/home/kroll/workingdir/wikipedia/relation_vocab_small.json"
RELATION_VOCAB_PERSON="/home/kroll/workingdir/wikipedia/relation_vocab_person.json"


# Analyze sentences
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/document/count_sentences.py $WIKIPEDIA_DOC_ENTITIES


# Export json content
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py $WIKIPEDIA_DOC -c scientists -d --format


# First perform Stanza NER
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists $WIKIPEDIA_DOC
# Perform EL with our dictionaries
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists -v $WIKIDATA_VOCAB --skip-load -f

# Next Delete all short entities


# run CoreNLP
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE_EXTRACATIONS  --no_entity_filter


# Load CoreNLP
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE_EXTRACATIONS -c scientists -et OPENIE_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE_EXTRACATIONS -c scientists -et OPENIE_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE_EXTRACATIONS -c scientists -et OPENIE_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE_EXTRACATIONS -c scientists -et OPENIE_SF --entity_filter only_subject_exact



# run OpenIE5.1
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie51/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE5_EXTRACATIONS  --no_entity_filter


# Load OpenIE5.1
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE5_EXTRACATIONS -c scientists -et OPENIE5_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE5_EXTRACATIONS -c scientists -et OPENIE5_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE5_EXTRACATIONS -c scientists -et OPENIE5_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE5_EXTRACATIONS -c scientists -et OPENIE5_SF --entity_filter only_subject_exact


# run OpenIE6
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS  --no_entity_filter

# Analyze extractions
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/analyze_openie_tuples.py $WIKIPEDIA_OPENIE6_EXTRACATIONS


# Load OpenIE6
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE6_EXTRACATIONS -c scientists -et OPENIE6_NF_NEW --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE6_EXTRACATIONS -c scientists -et OPENIE6_PF_NEW --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE6_EXTRACATIONS -c scientists -et OPENIE6_EF_NEW --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $WIKIPEDIA_OPENIE6_EXTRACATIONS -c scientists -et OPENIE6_SF_NEW --entity_filter only_subject_exact


# PathIE with relation vocab
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pipeline.py -c scientists -et PathIE --relation_vocab $RELATION_VOCAB_SMALL --workers 5


# canonicalize
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py -c scientists --relation_vocab $RELATION_VOCAB_SMALL --min_predicate_threshold 0

# with word embeddings
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py -c scientists --relation_vocab $RELATION_VOCAB_PERSON --min_predicate_threshold 0 --min_distance 1.0 --word2vec /home/jan/models/wiki.en.bin








#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. OpenIE6 NF Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. OpenIE6 NF Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $WIKIPEDIA_DOC $WIKIPEDIA_OPENIE6_EXTRACATIONS_TEST  --no_entity_filter 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. OpenIE6 NF Wikipedia: ${DIFF}s"


# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py -d -t --format json $WIKIPEDIA_DOC_ENTITIES -c scientists


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $WIKIPEDIA_DOC_ENTITIES $WIKIPEDIA_PATHIE_EXTRACATIONS_TEST  --relation_vocab $RELATION_VOCAB_SMALL --workers 32   2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. PathIE Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $WIKIPEDIA_DOC_ENTITIES $WIKIPEDIA_PATHIE_EXTRACATIONS_TEST  --relation_vocab $RELATION_VOCAB_SMALL --workers 32   2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. PathIE Wikipedia: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $WIKIPEDIA_DOC_ENTITIES $WIKIPEDIA_PATHIE_EXTRACATIONS_TEST  --relation_vocab $RELATION_VOCAB_SMALL --workers 32   2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. PathIE Wikipedia: ${DIFF}s"



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


# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/document/load_document.py $WIKIPEDIA_DOC -c scientists_benchmark

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists_benchmark -v $WIKIDATA_VOCAB --skip-load -f --workers 32 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. Vocab Linking Wikipedia: ${DIFF}s"

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists_benchmark -v $WIKIDATA_VOCAB --skip-load -f --workers 32 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. Vocab Linking Wikipedia: ${DIFF}s"

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists_benchmark -v $WIKIDATA_VOCAB --skip-load -f --workers 32  2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. Vocab Linking Wikipedia: ${DIFF}s"

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists_benchmark $WIKIPEDIA_DOC #2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. Stanza NER Wikipedia: ${DIFF}s"

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists_benchmark $WIKIPEDIA_DOC 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. Stanza NER Wikipedia: ${DIFF}s"

#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists_benchmark $WIKIPEDIA_DOC 2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. Stanza NER Wikipedia: ${DIFF}s"