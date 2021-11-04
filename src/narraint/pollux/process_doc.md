# Documentation of employing the KG Extraction Toolbox for a new domain

## Introduction
Our paper "A Toolbox for the Nearly-Unsupervised Construction of Digital Library Knowledge Graphs" has been successfully accepted and presented at the JCDL 2021. However, we were presented with the legitimate feedback, that using the Toolbox from start to finish for a new Domain still requires some imagination. In an effort to tackle this critique, we have decided to apply our toolbox in the domain of political science in cooperation with the "Fachinformationsdienst Politikwissenschaft - Pollux" of the TU BS.

This document seeks to document the process and steps of this endevour.

## First contact with the data

At the start of the project, Pollux supplied us with a jsonl file containing about 1.7 M documents with uids, titles and abstracts as well as some meta-information and keywords. For a first approach to this large corpus, a small subset (ca. 100 up to 1000 documents) will be processed and presented to the domain experts at Pollux.

### Translation and document loading
The first step in approaching this corpus of documents was to make it readable for our pipeline and load the documents into our database. In an effort to facilitate similar tasks in the future, the doctranslation module was created, which contains an abstract class for document translation and loading.

It was noticed that the interface between document translation/loading and entity linking is far from optimal, since our entity-linkin-scripts rely on json/pubtator input files and can't directly operate on the database. A solution to this has been proposed in issue #79.

### Entity linking with stanza
After translating and loading 