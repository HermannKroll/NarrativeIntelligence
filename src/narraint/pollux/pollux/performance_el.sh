

WIKIPEDIA_DOC="/home/kroll/workingdir/wikipedia/wikipedia_scientists.json"
WIKIDATA_VOCAB="/home/kroll/workingdir/wikipedia/wikidata_vocab.tsv"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists_benchmark $WIKIPEDIA_DOC 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "1. Stanza NER Wikipedia: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists_benchmark $WIKIPEDIA_DOC 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "2. Stanza NER Wikipedia: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists_benchmark $WIKIPEDIA_DOC 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "3. Stanza NER Wikipedia: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists_benchmark -v $WIKIDATA_VOCAB --skip-load -f --workers 32 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "1. Vocab Linking Wikipedia: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists_benchmark -v $WIKIDATA_VOCAB --skip-load -f --workers 32 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "2. Vocab Linking Wikipedia: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $WIKIPEDIA_DOC -c scientists_benchmark -v $WIKIDATA_VOCAB --skip-load -f --workers 32  2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "3. Vocab Linking Wikipedia: ${DIFF}s"



POLLUX_DOC="/home/kroll/workingdir/pollux/pollux_docs.json"
POLLUX_VOCAB="/home/kroll/workingdir/pollux/cwe_vocab.tsv"

python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/document/load_document.py $POLLUX_DOC -c pollux_benchmark 2>> /dev/null 1>>/dev/null

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c pollux_benchmark $POLLUX_DOC --skip-load  2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "1. Stanza NER Pollux: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c pollux_benchmark $POLLUX_DOC 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "2. Stanza NER Pollux: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c pollux_benchmark $POLLUX_DOC 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "3. Stanza NER Pollux: ${DIFF}s"


START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $POLLUX_DOC -c pollux_benchmark -v $POLLUX_VOCAB --skip-load -f --workers 32 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "1. Vocab Linking Pollux: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $POLLUX_DOC -c pollux_benchmark -v $POLLUX_VOCAB --skip-load -f --workers 32 2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "2. Vocab Linking Pollux: ${DIFF}s"

START=$(date +%s.%N)
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py $POLLUX_DOC -c pollux_benchmark -v $POLLUX_VOCAB --skip-load -f --workers 32  2>> /dev/null 1>>/dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "3. Vocab Linking Pollux: ${DIFF}s"


