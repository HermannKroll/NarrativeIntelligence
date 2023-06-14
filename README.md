# Narrative Service
Caution: This project includes research software and is still in development.
The project is mainly used for research.

It covers:
- The [narrative service](https://www.narrative.pubpharm.de) 
- Research/evaluation/brain storming scripts in the [analysis package](src/narraint/analysis)

It requires two subprojects:
- [Narrative Annotation](https://github.com/HermannKroll/NarrativeAnnotation): Pharmaceutical entity linking, entity handling, entity resolving (name to id)
- [KGExtractionToolbox](https://github.com/HermannKroll/KGExtractionToolbox): Basic entity linking methods / information extraction / pipelines for automatisation


To use this project, clone this project and its submodules via:
```
git clone --recurse-submodules --branch dev git@github.com:HermannKroll/NarrativeIntelligence.git
```


# Database Setup
The narrative service requires a Postgres database that contains processed documents. 
So first please setup a Postgres database by following the official instructions. 
We used V14. 
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
This line allows accessing the database from localhost. 

Now restore the database dump
``` 
pg_restore -h 127.0.0.1 -O -U postgres -W -d fidpharmazie fidpharmazie_2023_06_12.dump
``` 

After the database has been restored, we need to create an user for the database. 
Login into the database as the postgres user.
```
psql -h localhost -U postgres -W -d fidpharmazie
```
Create user for the service.
Please replace EXAMPLE_PW by a real password.
```
CREATE USER servicero WITH PASSWORD 'EXAMPLE_PW';
```

Now grant all required rights.
```
GRANT SELECT ON ALL TABLES IN SCHEMA public TO servicero;
GRANT INSERT ON TABLE public.PREDICATION_RATING TO servicero;
GRANT INSERT ON TABLE public.SUBSTITUTION_GROUP_RATING TO servicero;
```
Ratings must be inserted. For all other tables, read access is sufficient for the service to run. 

# Narrative Service Setup
The narrative service is written in Python. 
We need to create a suitable interpreter first.

## Create a virtual environment
We tested and used Python 3.8 and Conda. 
```
conda create -n narraint python=3.8
```

Activate the environment
```
conda activate narraint
```

## Getting Started
Install all Python requirements:
```
pip install -r requirements.txt
```


## Download Additional Data
Download the latest (currently 2022) MeSH Descriptor file. 
```
cd lib/NarrativeAnnotation/
bash download_data.sh
cd ../../
```



## Configuration
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
  "POSTGRES_HOST": "127.0.0.1",
  "POSTGRES_PORT": "5432",
  "POSTGRES_USER": "servicero",
  "POSTGRES_PW": "EXAMPLE_PW",
  "POSTGRES_SCHEMA": "public"
}
```

## Setup NLP 
Execute NLTK stuff.
```
python src/narraint/setup_nltk.py
```

## Build Required indexes 
We require two working indexes for several scripts:
The first script will build all necessary indexes (tagging, entity translation and services indexes). 
Make sure, that you are connected to the fidpharmazie database.
```
python src/narraint/build_all_indexes.py
```
This may take a while.



# Development

## Setting up the Test Suite
Just execute src/nitests folder via pytests.


## Project structure
The projects core, the `narraint` package, consists of several Python packages and modules with do a certain job:

| Package       | Task                                                                                          |
|---------------|-----------------------------------------------------------------------------------------------|
| `analysis`    | Python scripts to compute database statistics and research stuff                              |
| `atc`         | ATC Drug Classification stuff                                                                 |
| `backend`     | Connection to database, loading and exporting                                                 |
| `cleaning`    | Extraction DB cleaning (predicate cleaning and integrity constraints)                         |
| `extraction`  | Pharmaceutical extraction pipeline                                                            |
| `document`    | Narrative Document Class                                                                      |
| `frontend`    | Narrative Service Web Service                                                                 |
| `pubmedutils` | Wrapper classes for PubTator documents as well as useful functionality for PubTator documents |
| `queryengine` | Engine to match graph queries (basic graph patterns) to our database facts (retrieval)        

## General Database Schema
![DB Scheme](./docs/dbdiagram.png)

## Narrative Service Database Schema
![DB Scheme](./docs/dbdiagram_service.png)


# Development 
## SSH Server Interpreter
Check out the latest version of the project. 
Next open the project in PyCharm.
Next, configure the SSH Interpreter in PyCharm. 
Python Interpreter can be found in the local conda directory (.conda/...)
