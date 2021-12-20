python3.8 -u /home/jan/narint/src/narraint/pollux/load_wikipedia.py /home/jan/wikiextractor/extraction -c scientists -t "/home/jan/pollux_data/raw_input/Wikidata - Scientist with Wikipedia Article.tsv"
python3.8 -u /home/jan/narint/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py -c scientists -d --format json /home/jan/wikiextractor/raw_docs
python3.8 -u /home/jan/narint/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists /home/jan/wikiextractor/raw_docs
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/vocab_entity_linking.py wikipedia_scientists.json -c scientists -v wikidata_vocab.tsv --skip-load -f

# Export json content
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py wikipedia_scientists.json -c scientists -d

# run OpenIE
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pipeline.py -c scientists -et OpenIE51


# run PathIE
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pipeline.py -c scientists -et PathIE --workers 20

# Try PathIE with relation vocab
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/extraction/pipeline.py -c scientists -et PathIE --idfile einstein_id.txt --relation_vocab relation_vocab_small.json --workers 5

# canonicalize
python3 ~/KGExtractionToolbox/src/kgextractiontoolbox/cleaning/canonicalize_predicates.py -c scientists --relation_vocab relation_vocab_small.json --min_predicate_threshold 0