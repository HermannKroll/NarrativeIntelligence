# Narrative Intelligence Docker

This project can be used to perform Named Entity Recognition on documents in the PubTator format.


## Getting Started
First install Docker.
The Docker image is contained inside the ``narraint.tar.gz`` file. Then, load the image into Docker.
Next, create a Docker Volume for the database and for the temp files.

```
sudo apt install docker.io docker-compose

docker load < narraint.tar.gz

docker volume create narraint_postgres
docker volume create narraint_tmp
```

Now, you should choose a database password. Open the file ``docker-compose.yml`` and change 
the values behind ``POSTGRES_PASSWORD`` (line 13) and ``NI_POSTGRES_PW`` (line 31) from ``example`` 
to your custom password.

To create the database, run the following command:

```
docker-compose up psql
```

Quit using ``CTRL + C``.
Then, type ``docker-compose down`` for clean-up.


## Usage
Top run the program, open the file ``docker-compose.yml`` again. Now, you provide the directories for in- and output,
the collection name of the documents and the Entity types to tag.

Replace the `/path/to/input` in line 33 with the path to the directory containing the PubTator files.
Replace the `/path/to/output` in line 34 with the path to the output directory. The application is going to
create a file called `out.txt` in the output directory. Make sure, that no such file exists.

Line 36 contains the actual command for the application.
Replace `COLLECTION` with the name of the collection the documents belong to. The string should only contain
alphanumerical characters. **You can not change it afterwards, otherwise all documents are re-loaded into the database.** 

Line 36 also contains the Entity types to tag. After the `-t`, you can provide the following abbreviations:

| Abbreviation | Entity type |
|-------------------|-------------------|
| A | All |
| DF | Dosage Form |
| G | Gene |
| C D | Chemical and Disease (only supported together) |

The line `-c PubPharm -t DF C D` will load the documents into the collection
`PubPharm` and tag the entity types DosageForm, Chemical and Disease.

Finally, start the application with this command:

```
docker-compose up narraint
```

## PhpPgAdmin

For debugging purposes or similar, you can start PhpPgAdmin using ``docker-compose up admin``.
Access the GUI opening ``localhost:8080/`` in your browser. The username is `postgres` and the password 
the one you supplied in the *Getting started* section.