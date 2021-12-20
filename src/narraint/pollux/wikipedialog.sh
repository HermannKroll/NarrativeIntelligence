python3.8 -u /home/jan/narint/src/narraint/pollux/load_wikipedia.py /home/jan/wikiextractor/extraction -c scientists -t "/home/jan/pollux_data/raw_input/Wikidata - Scientist with Wikipedia Article.tsv"
python3.8 -u /home/jan/narint/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/export_annotations.py -c scientists -d --format json /home/jan/wikiextractor/raw_docs
python3.8 -u /home/jan/narint/lib/KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c scientists /home/jan/wikiextractor/raw_docs

