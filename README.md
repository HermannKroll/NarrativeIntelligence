# Narrative Intelligence

This project can be used to process documents using Narratives.

## Getting Started
Download the latest (currently 2020) MeSH Descriptor file. Then install the required Python packages. We recommend you to use Python 3.6 or higher.

```
./download_data.sh
pip install -r requirements.txt
```

### Data directory
The ``data`` directory contains application data for **all** packages.
Application data should **never** be stored inside the project models.
Application data includes:
- MESH descriptor files
- UMLS data
- TIB EPA dump

### Configuration
*All* configuration lives inside the `config` directory. The `*.example.json` files show the structure of the corresponding configuration file. Copy the example file and remove the `.example` from the filename. Note, the configuration files are referenced by the module `narraint.config`, so you shouldn't rename them.

The database can be configure with the file ``backend.json`` and using environment variables. The environment variables
are favoured over the `json`-configuration. 

| Name | Function |
| ------ | ------ |
| `NI_POSTGRES_USER` | Username |
| `NI_POSTGRES_PW` | Password |
| `NI_POSTGRES_HOST` | Host |
| `NI_POSTGRES_POST` | Port number |
| `NI_POSTGRES_DB` | Database name |


## Project structure
The projects core, the `narraint` package, consists of several Python packages and modules with do a certain job:

| Package | Task |
|-----------------|-----------------------------------------------------------------------------------------------|
| `backend` | Connection to database, loading and exporting |
| `enitity` | Entity stuff like mapping entity ids to vocabulary headings|
| `frontend` | Webserver the the user interface for querying with Narratives (FID Pharmazie) |
| `graph` | Model for a labeled directed graph with useful tools (computing connectivity components, export to dot, etc) |
| `mesh` | MeSH database wrapper, provides several functions to work on the MeSH tree |
| `narrative` | Implementation of the Narrative querying |
| `openie` | OpenIE for PubTator documents using Standford NLP |
| `preprocessing` | Conversion and Named Entity Recognition on PubTator documents |
| `pubmedutils` | Tools to query PMIDs from PubMed and PubTator files from Pubtator  |
| `pubtator` | Wrapper classes for PubTator documents as well as useful functionality for PubTator documents |
| `queryengine` | Engine to match graph queries (basic graph patterns) to our database facts (extracted by openie)  |
| `semmeddb` | Connection Handling for a SemMedDB. Currently our prototype queries SemMedDB via this package for fact retrieval |
| `stories` | Some experimental stuff to derive stories from documents |


## Named Entity Recognition

To perform Named Entity Recognition of documents use the `preprocessing` package. The documents must first be converted to the PubTator format ([example file](https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/pubtator?pmids=19894120)). Please note that the PubTator format is the central unit for this project and that all tools work with this format.

The entry point `preprocess.py` takes a directory of PubTator files and generates a single file with all documents and tags.
The documents and tags are all inserted into the database for later processing and retrieval.

Currently, the following entity types can be detected:
- Chemicals
- Diseases
- Genes
- Species
- Dosage Forms

The package provides APIs for several third-party taggers:

| Tagger | Entity types |
|-------------------|-------------------|
| TaggerOne (0.2.1) | Chemical, Disease |
| GNormPlus | Gene |
| DNorm | Disease |
| tmChem | Chemical |
| DosageFormTagger (own) | DosageForm

## Database scheme

![DB Scheme](./docs/dbdiagram.png)
created with app.quickdatabasediagrams.com


## Meeting Protocols
- [2020_03_25](meetings/2020_03_25.md)
- [2020_03_19](meetings/2020_03_19.md)
