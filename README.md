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
To run the service, only backend.json is required. 
The database can be configured with the file ``backend.json`` and using environment variables. 
The environment variables are favoured over the `json`-configuration. 

Next, configure your database connection in ``backend.json``:
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

## Python Path
Make always be sure that if you run any of our scripts, you activated your conda environment and set the Python Path.
```
conda activate narraint
export PYTHONPATH="/home/USER/NarrativeIntelligence/src/:/home/USER/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/home/USER/NarrativeIntelligence/lib/KGExtractionToolbox/src/"
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


# Web Server Deployment
The project builds upon Django which uses gunicorn as a local web server. 
However, gunicorn should not be used as a live web service. 
That is why a reverse proxy should be used to serve the static data and forward request to the local gunicorn. 


First, create a static www directory to store all static web files:
```
sudo mkdir /var/www/static
sudo chgrp -R www-data /var/www 
sudo chmod -R 775 /var/www
```

## Deploy a reverse proxy
We used nginx. 
Please install nginx.

Configure it via:
```
sudo nano /etc/nginx/nginx.conf
```

We used the following configuration:
- Gzip is required to shrink down large results
- HTTP is forwarded to HTTPS
- Proxy Headers are set to that gunicorn accepts the forwarded messages.
- We assume that gunicorn and Django will run on port 8080. This port must NOT be reachable from outside. 
```
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
        worker_connections 768;
        #multi_accept on;
}

http {
    sendfile on;

    gzip              on;
    gzip_http_version 1.0;
    gzip_proxied      any;
    gzip_min_length   500;
    gzip_disable      "MSIE [1-6]\.";
    gzip_types        text/plain text/xml text/css
                      text/comma-separated-values
                      text/javascript
                      application/x-javascript
                      application/atom+xml;


    proxy_connect_timeout       600;
    proxy_send_timeout          600;
    proxy_read_timeout          600;
    send_timeout                600;

    # Configuration for Nginx
    server {
        listen 80;
        server_name www.narrative.pubpharm.de;
        return 301 https://narrative.pubpharm.de$request_uri;
    }

    server {
        # Running port
        listen 443 ssl;
        server_name www.narrative.pubpharm.de;
        ssl_certificate  /etc/nginx/narrative.pubpharm.de.pem;
        ssl_certificate_key /etc/nginx/narrative.pubpharm.de.key;
        ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # Settings to serve static files 
        location ~ ^/static/  {
            include  /etc/nginx/mime.types;
            root /var/www/;
        }

        # Proxy connections to the application servers
        # app_servers
        location / {
            proxy_pass         http://127.0.0.1:8080;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Host $server_name;
            proxy_set_header X-Forwarded-Proto $scheme;
            add_header Front-End-Https on;
         
        }
    }
}
```
For SSL, we copied certificate and private key to
```
/etc/nginx/narrative.pubpharm.de.pem
/etc/nginx/narrative.pubpharm.de.key
```

After configuring nginx, please restart it via:
```
sudo service nginx restart 
```

## Setup DJango and gunicorn

Switch into a screen session for the following commands.
```
screen
```

Make always be sure that if you run any of our scripts, you activated your conda environment and set the Python Path.
```
conda activate narraint
export PYTHONPATH="/home/USER/NarrativeIntelligence/src/:/home/USER/NarrativeIntelligence/lib/NarrativeAnnotation/src/:/home/USER/NarrativeIntelligence/lib/KGExtractionToolbox/src/"
```

The productive settings must be set for Django via:
```
export DJANGO_SETTINGS_MODULE="frontend.settings.prod"
```

Next, copy all static web data to the reverse proxy. 
Therefore, run the following lines:
```
sudo chmod -R 777 /var/www
python ~/NarrativeIntelligence/src/narraint/frontend/manage.py collectstatic
sudo chmod -R 775 /var/www	 
```
The script will inform you how many files are going to be changed. 
Accept the changes with 'y'.

## Run Django and gunicorn
```
cd ~/NarrativeIntelligence/src/narraint/frontend/

gunicorn -b 127.0.0.1:8080 --timeout 500 frontend.wsgi -w 4 --preload 2> ~/run_2023_06_X.txt
```

At the moment, logging is done on console. 
That is why we redirect the output to a file.
- w specifies the number of parallel worker (each one consumes about 2GB of RAM)
- preload forces that all indexes are load before spawning the workers
- timeout specifies when a long request will be stopped and the corresponding worker is rebooted


# Updating the Service Data


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


## SSH Server Interpreter
Check out the latest version of the project. 
Next open the project in PyCharm.
Next, configure the SSH Interpreter in PyCharm. 
Python Interpreter can be found in the local conda directory (.conda/...)


## General Database Schema
![DB Scheme](./docs/dbdiagram.png)

## Narrative Service Database Schema
![DB Scheme](./docs/dbdiagram_service.png)

