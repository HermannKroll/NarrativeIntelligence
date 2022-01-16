#python3.8 -u /home/jan/narint/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py -c pollux -d --format json /home/jan/wikiextractor/raw_docs


# python3.8 -u /home/jan/narint/src/narraint/pollux/load_POLLUX.py /home/jan/wikiextractor/extraction -c pollux -t "/home/jan/pollux_data/raw_input/Wikidata - Scientist with POLLUX Article.tsv"
#
#

POLLUX_DOC="/home/kroll/workingdir/pollux/pollux_docs.json"
POLLUX_DOC_ENTITIES="/home/kroll/workingdir/pollux/pollux_docs_with_entities.json"
POLLUX_VOCAB="/home/kroll/workingdir/pollux/cwe_vocab.tsv"

POLLUX_OPENIE_EXTRACATIONS="/home/kroll/workingdir/pollux/extractions/openie.tsv"
POLLUX_OPENIE5_EXTRACATIONS="/home/kroll/workingdir/pollux/extractions/openie51.tsv"
POLLUX_OPENIE6_EXTRACATIONS="/home/kroll/workingdir/pollux/extractions/openie6.tsv"

POLLUX_PATHIE_EXTRACATIONS_TEST="/home/kroll/workingdir/pollux/extractions/pathie_benchmark.tsv"
POLLUX_OPENIE6_EXTRACATIONS_TEST="/home/kroll/workingdir/pollux/extractions/openie6_benchmark.tsv"

RELATION_VOCAB_SMALL="/home/kroll/workingdir/POLLUX/relation_vocab_small.json"

# Analyze sentences
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/document/count_sentences.py $POLLUX_DOC_ENTITIES



# Export json content
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py $POLLUX_DOC -c pollux -d --format json

# Export json documents with entities
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py $POLLUX_DOC_ENTITIES -c pollux -d -t --format json

# First perform Stanza NER
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c pollux $POLLUX_DOC
# Perform EL with our dictionaries
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $POLLUX_DOC -c pollux -v $POLLUX_VOCAB --skip-load -f

# Next Delete all short entities


# run CoreNLP
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie/main.py $POLLUX_DOC $POLLUX_OPENIE_EXTRACATIONS  --no_entity_filter


# Load CoreNLP
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE_EXTRACATIONS -c pollux -et OPENIE_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE_EXTRACATIONS -c pollux -et OPENIE_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE_EXTRACATIONS -c pollux -et OPENIE_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE_EXTRACATIONS -c pollux -et OPENIE_SF --entity_filter only_subject_exact



# run OpenIE5.1
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie51/main.py $POLLUX_DOC $POLLUX_OPENIE5_EXTRACATIONS  --no_entity_filter


# Load OpenIE5.1
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE5_EXTRACATIONS -c pollux -et OPENIE5_NF --entity_filter no_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE5_EXTRACATIONS -c pollux -et OPENIE5_PF --entity_filter partial_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE5_EXTRACATIONS -c pollux -et OPENIE5_EF --entity_filter exact_entity_filter
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE5_EXTRACATIONS -c pollux -et OPENIE5_SF --entity_filter only_subject_exact


# run OpenIE6
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/openie6/main.py $POLLUX_DOC $POLLUX_OPENIE6_EXTRACATIONS  --no_entity_filter
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/analyze_openie_tuples.py $POLLUX_OPENIE6_EXTRACATIONS

# Load OpenIE6
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE6_EXTRACATIONS -c pollux -et OPENIE6_NF_NEW --entity_filter no_entity_filter
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE6_EXTRACATIONS -c pollux -et OPENIE6_PF_NEW --entity_filter partial_entity_filter
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE6_EXTRACATIONS -c pollux -et OPENIE6_EF_NEW --entity_filter exact_entity_filter
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/loading/load_openie_extractions.py $POLLUX_OPENIE6_EXTRACATIONS -c pollux -et OPENIE6_SF_NEW --entity_filter only_subject_exact


# PathIE with relation vocab
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pipeline.py -c pollux -et PathIE --relation_vocab $RELATION_VOCAB_SMALL --workers 5


# canonicalize
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py -c pollux --relation_vocab relation_vocab_small.json --min_predicate_threshold 0

# with word embeddings
# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py -c pollux --relation_vocab relation_vocab_person.json --min_predicate_threshold 0 --min_distance 1.0 --word2vec /home/jan/models/wiki.en.bin








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


# python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py -d -t --format json $POLLUX_DOC_ENTITIES -c pollux


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $POLLUX_DOC_ENTITIES $POLLUX_PATHIE_EXTRACATIONS_TEST  --relation_vocab $RELATION_VOCAB_SMALL --workers 32   2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "1. PathIE POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $POLLUX_DOC_ENTITIES $POLLUX_PATHIE_EXTRACATIONS_TEST  --relation_vocab $RELATION_VOCAB_SMALL --workers 32   2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "2. PathIE POLLUX: ${DIFF}s"


#START=$(date +%s.%N)
#python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pathie/main.py $POLLUX_DOC_ENTITIES $POLLUX_PATHIE_EXTRACATIONS_TEST  --relation_vocab $RELATION_VOCAB_SMALL --workers 32   2>> /dev/null 1>>/dev/null
#END=$(date +%s.%N)
#DIFF=$(echo "$END - $START" | bc)
#echo "3. PathIE POLLUX: ${DIFF}s"



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