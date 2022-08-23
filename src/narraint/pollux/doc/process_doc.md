# Documentation of employing the KG Extraction Toolbox for a new domain

## Introduction
Our paper "A Toolbox for the Nearly-Unsupervised Construction of Digital Library Knowledge Graphs" has been successfully accepted and presented at the JCDL 2021. However, we were presented with the legitimate feedback, that using the Toolbox from start to finish for a new Domain still requires some imagination. In an effort to tackle this critique, we have decided to apply our toolbox in the domain of political science in cooperation with the "Fachinformationsdienst Politikwissenschaft - Pollux" of the TU BS.

This document seeks to document the process and steps of this endevour.

## First contact with the data

At the start of the project, Pollux supplied us with a jsonl file containing about 1.7 M documents with uids, titles and abstracts as well as some meta-information and keywords. For a first approach to this large corpus, a small subset (ca. 100 up to 1000 documents) will be processed and presented to the domain experts at Pollux.

### Translation and document loading
The first step in approaching this corpus of documents was to make it readable for our pipeline and load the documents into our database. In an effort to facilitate similar tasks in the future, the doctranslation module was created (doctranslation.py), which contains an abstract class for document translation and loading.

A subclass for reading the pollux corpus was created (translate_pollux.py) and run with

`python3 src/narraint/pollux/translate_pollux.py data/pollux_abstracts_100.jsonl tmp/pollux_translation.json -c pollux -d -l`

Even though the command above already exports the new documents, an export from the database was performed afterwards. this is due to the fact, that the command either loads the files to the translation table, thus creating duplicate entries or only outputs files that has not already been in the database. Therefore, an export is necessary if the output file is lost.

`python3 KGExtractionToolbox/src/kgextractiontoolbox/document/export.py -c pollux -d --format json tmp/pollux_translation.json`

It was noticed that the interface between document translation/loading and entity linking is far from optimal, since our entity-linkin-scripts rely on json/pubtator input files and can't directly operate on the database. A solution to this has been proposed in issue #79.

### Entity linking with stanza
stanza can be run on the exported documents.

`python3 KGExtractionToolbox/src/kgextractiontoolbox/entitylinking/stanza_ner.py -c pollux /home/jan/out/pollux_translation.json --skip-load`

this produced 212 tags in total. The distribution in tags per document is as follows:

|tags per doc|num docs|
|------------|--------|
|0           |49      |
|1           |17      |
|2           |8       |
|3           |7       |
|4           |6       |
|5           |2       |
|6           |2       |
|7           |1       |
|8           |3       |
|11          |3       |
|12          |2       |
|24          |1       |

### Fact extractions with OpenIE

Since the extraction scripts also require json files as inputs (see issue above), another export is necessary, this time with tags:

`python3 KGExtractionToolbox/src/kgextractiontoolbox/document/export.py -c pollux -d -t --format json tmp/pollux_translation.json`

