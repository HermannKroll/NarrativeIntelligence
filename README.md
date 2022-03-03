# Narrative Intelligence
Caution: This project includes research software and is still in development.
The project is mainly used for research.

It covers:
- The [narrative service](http://134.169.32.177) 
- Research/evaluation/brain storming scripts in the [analysis package](src/narraint/analysis)

It requires two subprojects:
- [Narrative Annotation](https://github.com/HermannKroll/NarrativeAnnotation): Pharmaceutical entity linking, entity handling, entity resolving (name to id)
- [KGExtractionToolbox](https://github.com/HermannKroll/KGExtractionToolbox): Basic entity linking methods / information extraction / pipelines for automatisation


To use this project, clone this project and its submodules via:
```
git clone --recurse-submodules --branch dev git@github.com:HermannKroll/NarrativeIntelligence.git
```

# Getting Started
Install all Python requirements:
```
pip install -r requirements.txt
```

Download the latest (currently 2022) MeSH Descriptor file. Then install the required Python packages. We recommend you to use Python 3.6 or higher.
```
bash lib/NarrativeAnnotation/download_data.sh
```


### Configuration
*All* configuration lives inside the `config` directory. 
The `*.example.json` files show the structure of the corresponding configuration file. 
Copy the example file and remove the `.example` from the filename.

The database can be configured with the file ``backend.json`` and using environment variables. 
The environment variables are favoured over the `json`-configuration. 


Next, configure your database connection. 
```
```


## Build Indexes
We require two working indexes for several scripts:

The first script will build indexes that allow us to translate entity ids into names etc.
```
python lib/NarrativeAnnotation/src/narrant/build_indexes.py
```

The second index is required to work with our Narrative Web service.
```
python src/narraint/build_all_indexes.py
```

# SSH Server Interpreter
Check out the latest version of the project. 
Next open the project in PyCharm.

Create a virtual environment on the server.
```
conda create --n env python=3.8 anaconda
```

Accept installing all packages. 
Next, configure the SSH Interpreter in PyCharm. 
Python Interpreter can be found in the local conda directory (.conda/...)



# Additional Shared Resource Directory
We have a shared Cloud Space: [OneDrive](https://1drv.ms/u/s!ArDgbq3ak3Zuh5oNxxBPfJSqqpB2cw?e=iMfQKR). Password: youshallnotpass


# Data Dumps on our Server
| Name | Description | Path on IS69 | 
| ------ | ------ | ------ | 
| PubMed | PubMed Medline Data | /hdd2/datasets/pubmed_medline/ |
| ZBMed | Covid 19 Pre-Prints | /hdd2/datasets/zbmed |


## Project structure
The projects core, the `narraint` package, consists of several Python packages and modules with do a certain job:

| Package | Task |
|-----------------|-----------------------------------------------------------------------------------------------|
| `analysis` | Python scripts to compute database statistics and research stuff |
| `atc` | ATC Drug Classification stuff |
| `backend` | Connection to database, loading and exporting |
| `cleaning` | Extraction DB cleaning (predicate cleaning and integrity constraints) |
| `document` | Narrative Document Class |
| `frontend` | Narrative Service Web Service |
| `pubtator` | Wrapper classes for PubTator documents as well as useful functionality for PubTator documents |
| `queryengine` | Engine to match graph queries (basic graph patterns) to our database facts (retrieval)

## General Database Schema
![DB Scheme](./docs/dbdiagram.png)

## Narrative Service Database Schema
![DB Scheme](./docs/dbdiagram_service.png)


