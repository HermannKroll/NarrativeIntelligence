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

# Create a virtual environment
We recommend to use at least Python 3.8
```
conda create -n narraint python=3.8
```

Activate the environment
```
conda activate narraint
```

# Getting Started
Install all Python requirements:
```
pip install -r requirements.txt
```


# Download Additional Data
Download the latest (currently 2022) MeSH Descriptor file. 
```
cd lib/NarrativeAnnotation/
bash download_data.sh
cd ../../
```


### Configuration
*All* configuration lives inside the `config` directory. 
The `*.example.json` files show the structure of the corresponding configuration file. 
Copy the example file and remove the `.example` from the filename.

The database can be configured with the file ``backend.json`` and using environment variables. 
The environment variables are favoured over the `json`-configuration. 


Next, configure your database connection. 
The latest version should look like:
```
{
  "use_SQLite": false,
  "SQLite_path": "sqlitebase.db",
  "POSTGRES_DB": "fidpharmazie",
  "POSTGRES_HOST": "134.169.32.169",
  "POSTGRES_PORT": "5432",
  "POSTGRES_USER": "tagginguser",
  "POSTGRES_PW": "u3j4io1234u8-13!14",
  "POSTGRES_SCHEMA": "public"
}
```


## Build Indexes
We require two working indexes for several scripts:

The first script will build all necessary indexes (tagging, entity translation and services indexes). 
Make sure, that you are connected to our fidpharmazie database.
```
python3 src/narraint/build_all_indexes.py
```

Note, both scripts can be executed via the remote interpreter :)

## Setup NLP 
Execute NLTK stuff.
```
python3 src/narraint/setup_nltk.py
```

# Setting up the Test Suite
Just execute src/nitests folder via pytests.

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


# Development 
## SSH Server Interpreter
Check out the latest version of the project. 
Next open the project in PyCharm.

Create a virtual environment on the server.
```
conda create --n env python=3.8 anaconda
```

Accept installing all packages. 
Next, configure the SSH Interpreter in PyCharm. 
Python Interpreter can be found in the local conda directory (.conda/...)


# Database

Create a new postgres database. 
Log in first.
```
psql -h localhost -U postgres -W
```

Create the database.
```
CREATE DATABASE fidpharmazie;
```


Edit the following file
```
nano /etc/postgresql/14/main/pg_hba.conf
```
by adding the line
``` 
host    fidpharmazie    all             127.0.0.1/32            md5
```

Now restore the database dump
``` 
pg_restore -h 127.0.0.1 -O -U postgres -W -d fidpharmazie fidpharmazie_2023_06_12.dump
``` 