# Data Mining (Update Service Data)
The service uses our database model. 
However, the data mining (entity linking and statement extraction) is implemented in the NarrativeAnnotation package.
So, please read the instructions of our [NarrativeAnnotation GitHub Page](https://github.com/HermannKroll/NarrativeAnnotation/blob/main/README.md). 
NarrativeAnnotation contains all scripts to transform biomedical documents into graphs.

# Update Mining Pipeline
```
cd ~/NarrativeIntelligence/
git pull --recurse-submodules
```

Upgrade pip requirements:
```
conda activate narrant
pip install --upgrade -r ~/NarrativeIntelligence/requirements.txt
pip install --upgrade -r ~/NarrativeAnnotation/requirements.txt
pip install --upgrade -r ~/NarrativeAnnotation/lib/KGExtractionToolbox/requirements.txt
```


## Setup configurations
mv ~/NarrativeAnnotation/config/*.json ~/NarrativeIntelligence/config/

Jump into the python environment:
```
conda activate narrant
```

Next setup the Python path:

As pubpharm user:
```
export PYTHONPATH="/home/pubpharm/NarrativeIntelligence/src/:/home/pubpharm/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/home/pubpharm/NarrativeIntelligence/lib/KGExtractionToolbox/src/"
```

As root:
```
export PYTHONPATH="/root/NarrativeIntelligence/src/:/root/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/root/NarrativeIntelligence/lib/KGExtractionToolbox/src/"
```


# Full Automation of all Pipelines
We created one script to execute all pipelines. 
The script will send a mail if an error occurs. 
Therefore, create a mailenv:
```
cd ~/NarrativeIntelligence/scripts/
nano source .mailenv
```

Edit the following lines:
```
ADDRESS="target@beispiel.de"
SENDER="from@beispiel.de (Narrative Service Updater)"
```
Save it.

For the complete pipeline run:
```
bash ~/NarrativeIntelligence/scripts/all_pipeline_updates.sh
```

# Automated Index Pipelines
We wrote a script to automate the whole service update procedure. 
The script can be found in [scripts/update_service_data.sh](scripts/update_service_data.sh).

Make sure that +x is set for the script:
```
chmod +x scripts/update_service_data.sh
```

You may have to open the script and adjusts paths (e.g., where to store the latest predication id).
```
nano scripts/update_service_data.sh
```

**Make sure** that the file $PREDICATION_MINIMUM_UPDATE_ID_FILE exists and stores the latest predication id.


Make sure that the virtual environment narrant is activated and that your Python path is configured properly. 
Then run the bash script. This may take a while.
```
bash scripts/update_service_data.sh
```

## Periodic Updates
There are some indexes and tables which only need updates in once in a while. 
We build pipelines to execute all necessary scripts (see details below). 


Update every six months: [updates_every_6_months.sh](scripts/updates_every_6_months.sh)
```
bash scripts/updates_every_6_months.sh
```




## Detailed scripts Update Service Reverse Indexes
As soon as the database is updated, the service requires an update of tables for reverse indexes and metadata. 

The following script will join the Document, DocumentMetadata and Predication table to update the DocumentMetadataService table. 
The DocumentMetadataService table stores title and metadata of documents that are relevant for the service, i.e., at least a single statement was extracted from them. 
Otherwise the document will not appear in any query result in the service and is thus not relevant for the service.

Make sure that the virtual environment narrant is activated and that your Python path is configured properly. 
Please run the following script:
```
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/prepare_metadata_for_service.py
```

Next, the reverse index tables for statements and detected entities must be updated. 
Briefly, these indexes map a statement/entity to a set of documents, from which it was extracted/detected. 
We support two options: 
First, the whole index can be recreated (this will take time and consumes memory).
Therefore, run:
```
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py 
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py
```

However, the whole index creation might consume much memory. 
We support a low memory mode.
Run:
```
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --low_memory
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py --low_memory
```

This mode will take more time but less memory.
You may also adjust the buffer size (how much memory can be consumed):

```
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py \
   --low_memory --buffer_size 1000
   
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py \
    --low_memory --buffer_size 1000
```



There is an alternative to recreating the whole index. 
We support to specify the minimum predication id. 
The idea is that only documents are updated in the index which are new since the last index update.
Therefore, all predication entries are queried that have an id greater equal the minimum predication id.
This mode is way faster and less memory intensive than recreating the whole index.
Run: 
```
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_predication.py --predicate_id_minimum $PREDICATION_MINIMUM_UPDATE_ID
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/index/compute_reverse_index_tag.py --predicate_id_minimum $PREDICATION_MINIMUM_UPDATE_ID
```

Please note that the low memory mode and buffer size cannot be combined with the delta mode (predication id minimum).


You can export the latest predication id via:
```
python ~/mining/NarrativeIntelligence/lib/KGExtractionToolbox/src/kgextractiontoolbox/backend/export_highest_predication_id.py $PREDICATION_MINIMUM_UPDATE_ID_FILE
```
Replace $PREDICATION_MINIMUM_UPDATE_ID_FILE by a concrete path. 


Finally, we can update the database table that stores the date of the latest update via:
```
python ~/mining/NarrativeIntelligence/src/narraint/queryengine/update_database_update_date.py
```


There are some indexes that do not require a rebuilding every time. 
They are based on statistics of the database.
However, it might be a good idea to update them in periodic times.

First, there are indexes for the entity translation, explanation and autocompletion.
Run:
```
python ~/NarrativeIntelligence/src/narraint/build_all_indexes.py --force
```

**--force** enforces the creation without asking whether you are connected to the right DB first.
This is necessary for a automated script.

Next, we have a schema graph support information table to support the keyword to query graph translation.
To update this table, run:
```
python ~/NarrativeIntelligence/src/narraint/keywords2graph/schema_support_graph.py
```

The Drug Overviews show keyword clouds to the users. 
These clouds can be updated via:
```
python ~/NarrativeIntelligence/src/narraint/keywords/generate_drug_keywords.py
```

The word clouds for COVID-19 and Long COVID can be updated by:
```
python ~/NarrativeIntelligence/src/narraint/keywords/generate_covid_keywords.py
```

The trial status of drug disease indications is pre-computed by crawling ClinicalTrials.gov. 
The data should be updated in periodic intervalls (but not in every service update). 
To recompute the drug disease indications from ClinicalTrials.gov, run:
```
python ~/NarrativeIntelligence/src/narraint/clinicaltrials/extract_trial_phases.py
```



## Vacuum Database tables
The service database might degenerate over time if too many updates happen. 
It might be a good idea then to vacuum full every database table (rewrite + recreate indexes). 
Therefore, we prepared a set of SQL statements in [vacuum_db.sql](sql/vacuum_db.sql).

Either log in your postgres user, open a psql shell and paste the statements manually:
```
sudo su postgres
psql
```

Or execute them via psql and an explict user login:
```
psql "host=127.0.0.1 port=5432 dbname=fidpharmazie user=USER password=PW" -f $VACUUM_SQL
```
The user needs to have write access on the database tables.


## Vocabularies Updates
If the vocabularies have been updated, the service requires new indexes to translate strings to entity ids.
Make sure, that you are connected to the fidpharmazie database.
Run:
```
python src/narraint/build_all_indexes.py
```
Indexes should now be up-to-date.

## Data Dummy Generation
We support an option to create artificial data for test purposes. 
Do not run the script on your productive db.
Your user must have privileges for the DB (see step before).

```
python src/narraint/dummy/generate_dummy_data.py DOCS
```

**DOCS** is an integer about how many documents + data should be generated.
The script will generate:
- documents
- tags
- sentences
- predications

The argument **--incremental** will only add data incrementally and does not delete the collection before.
```
python src/narraint/dummy/generate_dummy_data.py DOCS --incremental
```

Usually, the Object-Relational Mapper (SQLAlchemy) will create the database tables if a session is created.
However, if you just need to create the data model + tables without doing anything, you can execute the following script:

```
python src/narraint/backend/create_database.py
```