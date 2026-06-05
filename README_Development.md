# Narrative Service Development Setup
This document describes the setup of a PyCharm IDE to develop on the Narrative Service.

## System Requirements

Two different methodologies exist to develop and run the NarrativeService:
- Local development: This requires the existence of a (remote) database connection. An SSH connection forwarding relevant ports is necessary.
- Remote development via SSH (using PyCharm Professional): by using the SSH connection, the project can be edited locally and executed remotely.

First, the [Local Development](#local-development-1-narrative-service-setup) is described, and the [Remote Development](#remote-development-1-create-python-virtual-environment) afterward.
The process of cloning the database is discussed in the first step [0. Prerequisites](#0-prerequisites).
This needs to be done for both methods.

The following two things are assumed to exist already:
- server user `pubpharm`
- postgres database `fidpharmazie`

> Important information for Mac-Users can be found under [Mac Development](#mac-development-apple-silicon).

## References:
- [PyCharm SSH Interpreter](https://www.jetbrains.com/help/pycharm/configuring-remote-interpreters-via-ssh.html)
- [PyCharm Django Setup](https://www.jetbrains.com/help/pycharm/creating-and-running-your-first-django-project.html)
- [Anaconda Docs](https://www.anaconda.com/docs/getting-started/anaconda/install#linux-installer)

## 0. Prerequisites

Since the development requires an active database connection, it needs to be initialized beforehand.
It is recommended to not use the production database for development, instead, create a copy of it.

The following commands assume that a production database with the name `fidpharmazie` and the owner `pubpharm` exists (as created in with [Service-Readme](README_Service.md)).
The easiest way of cloning the database is by executing the commands as the `postgres` superuser.
The process consist of a backup procedure and the restore of that.
It creates a new database with the name `fidpharmazie-dev` using `fidpharmazie` as template:

```bash
su postgres
pg_dump -h 127.0.0.1 -d fidpharmazie -F c -f fidpharmazie.dump
pg_restore --dbname=fidpharmazie-dev fidpharmazie.dump
rm -f fidpharmazie.dump
exit
```

The following steps depend on whether to develop locally or remote.
For local development, the next step is the following section [Local Development](#local-development-1-narrative-service-setup).
For remote development, the next step is section [Remote Development](#remote-development-1-create-python-virtual-environment).

## Local-Development-1: Narrative Service Setup

In PyCharm, first a new project has to be created.

### Create and configure local project

The simplest method is to directly initialize it from GitHub:
1. Click on **Project from Version Control...**
2. Insert **URL** `git@github.com:HermannKroll/NarrativeIntelligence.git`
3. Insert a path, e.g., `/path/to/NarrativeIntelligence`
4. Click on **Clone**
*...this may take a while...*
It may appear a window to create a new virtual environment (Python Interpreter).
Close it since we want to create a virtual environment using conda.

## Local-Development-2: Create a local interpreter

The next step is to create a local python interpreter (using conda).
1. Open **Settings**
2. Search for `Python Interpreter`
3. Click on **Add Interpreter** and select **Add local Interpreter**
4. Select *Generate new*
5. Select type **Conda**
6. Python version **3.10**
7. Choose a name, e.g., `narraint-dev`

> If you have not installed conda yet, the window will provide a clickable link to install the conda executable.
You need to click on **install conda**.

8. Click on **ok** to create the environment.

Next, the modules need to be installed.
Make sure, that the newly created environment is selected:
If you do not already see the active interpreter in the footer, you can visualize it by left-clicking on a footer-element and select `Python-Interpreter` as well.

To install the requirements, open the following files, hover over one of the underlined elements and click on `Install all missing packages`.
- `NarrativeIntelligence/requirements.txt`
- `NarrativeIntelligence/lib/NarrativeAnnotation/requirements.txt`
- `NarrativeIntelligence/lib/KGExtractionToolbox/requirements.txt`
After the interpreter has indexed the newly added requirements, none of them should have an underline anymore.
Alternatively, this can be done using the PyCharm console:

```bash
cd ~/path/to/NarrativeIntelligence
python -m pip install -r requirements.txt \
                      -r lib/NarrativeAnnotation/requirements.txt \
                      -r lib/KGExtractionToolbox/requirements.txt
```

> It might be the case that the installation fails at some point.
Missing packages can easily be installed afterward.
For example, the package `sphinx` (from requirements.txt) can be installed with: `python -m pip install sphinx~=2.3.1`.
Make sure that you have selected the right python environment.
This can be checked with `python -c "import sys;print(sys.executable)`.
It should be something like `/path/to/miniconda3/envs/narraint-dev/python.exe`.

## Local-Development-3: Configure the service

All configuration lives inside the `NarrativeIntelligence/config` directory. 
The `*.prod.json` files show the structure of the corresponding configuration file. 
Copy the example file and remove the `.prod` from the name. 
This need to be done each of the three files: `backend.json`, `entity_linking.json`, and `nlp.json`.

Next, configure the database connection in `backend.json`.
Open the file and insert the postgres username and password to get access to the `fidpharmazie` database.
```json
{
  "use_SQLite": false,
  "SQLite_path": "sqlitebase.db",
  "POSTGRES_DB": "fidpharmazie-dev",
  "POSTGRES_HOST": "127.0.0.1",
  "POSTGRES_PORT": "5432",
  "POSTGRES_USER": "pubpharm",
  "POSTGRES_PW": "POSTGRES_PASSWORD",
  "POSTGRES_SCHEMA": "public"
}
```

As a last step, mark each `src` folder as `Sources Root`.
Therefore, right-click on the `NarrativeIntelligence/src` folder and select `Mark directory as` - `Sources Root`.
Repeat the process for the source folders in `lib/NarrativeAnnotation/src` and `lib/KGExtractionToolbox/src`.

## Local-Development-4: Download external dependencies

To build the indexes locally, some external dependencies need to be downloaded first.
Therefore, execute the following script in the PyCharm console:
```bash
cd lib/NarrativeAnnotation/
bash download_data.sh
```

## Local-Development-5: Create Django Executable in PyCharm

Now, you are ready create a run config for the service application.
Open run configurations and configure remote interpreter for new Django application (top Right):

1. Click on **Edit Configurations...**
2. Create new `Python` run configuration by clicking on **+** on the left (Add new configuration)
3. Select remote Conda Interpreter (`narraint-dev`)
4. Select **script** path `/path/to/NarrativeIntelligence/src/narraint/frontend/manage.py`
5. Insert **Script parameter**: `runserver`
6. Insert **Working Directory**: `/path/to/NarrativeIntelligence/src/narraint/frontend`
7. Append the **Environment Variables:** with `PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=frontend.settings.dev`
8. Click on **Apply** and close the window

Now, the Django Server can be started.

### Activate SSH Port Forwarding for the Database

To connect to the remote database service, the last step is to forward the required port.
By default, the port is set to `5432`.
If it is changed on the remote server, the corresponding parameter `POSTGRES_PORT` needs to be changed in the configuration file (`backend.json`).

Start a terminal and execute the following command:
```bash
ssh -L 5432:localhost:5432 pubpharm@<SERVER-ADDR>
```

> **Note** that those connections need to be alive when the service runs.

### Finally: Start the Narrative Service

If everything works correctly, the server starts (after clicking on the `green triangle` on the top left).
When the initialization is finished the IP address will show up to access the service.
Open the ip address with the browser.

Congratulations, you have done it.

## Local-Development-6: Create Unit-Tests Executables in PyCharm

The service comes with a bunch of unit tests to ensure that it works as expected.
Each set of tests is located as a subdirectory of the source folders, namely `nitests` (`src/nitest`), `narranttests` (`lib/NarrativeAnnotation/src/narranttests`), and `kgtests` (`lib/KGExtractionToolbox/src/kgtests`).

To run on of the tests, create a new run configuration (as for step 6).
1. Select the run-config type `Python tests` - `Autodetect`
2. Select the remote interpreter `narraint-dev`
3. Choose to execute a `Script` 
4. Enter the **Script path** to the test root, e.g., `/path/to/NarrativeIntelligence/src/nitests`
5. Enter the same path at **Working directory**
6. Click on **Apply** and close the window

Select the freshly created run-config and execute it.
The tests should be detected automatically.

## Remote-Development-1: Create Python Virtual Environment

For the first step, connect to the remote server with a SSH session and login into the pubpharm user.
Download the latest version of Anaconda. (If not already existent)
Note that the used version might have been updated already.
If necessary, check for newer versions on the anaconda [website](https://www.anaconda.com/docs/getting-started/anaconda/install#linux-installer).

```bash
cd ~
curl -O https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Linux-x86_64.sh
```

Install anaconda.

```bash
bash ~/Anaconda3-2024.10-1-Linux-x86_64.sh
```

Proceed with the installation.
The default installation path `/home/pubpharm/anaconda3` should be sufficient.
Choose `YES` to allow Conda to modify your shell configuration to support Conda commands.
Use the following command to refresh the terminal session.

```bash
source ~/.bashrc
```

Conda can now be used.
To finish the installation, initialize Conda.

```bash
conda init
```
As the next step, create a virtual environment.
The Narrative Service is based on Python version 3.10.

```bash
conda create -n narraint-dev python=3.10
```

Last, activate the newly created environment `narraint-dev`.

```bash
conda activate narraint-dev
```

## Remote-Development-2: Narrative Service Setup (Remote)

Now, create the directory on the server where the project should be live.
The project does not need to be cloned since we deploy it later from the local setup.

```bash
mkdir /home/pubpharm/dev/NarrativeIntelligence
```

## Remote-Development-3: Narrative Service Setup (Local)

In PyCharm, first a new project has to be created.

### Create and configure local project

The simplest method is to directly initialize it from GitHub:
1. Click on **Project from Version Control...**
2. Insert **URL** `git@github.com:HermannKroll/NarrativeIntelligence.git`
3. Insert a path, e.g., `/path/to/NarrativeIntelligence`
4. Click on **Clone** *...this may take a while...*

Next, the remote interpreter needs to be added:

1. Open Settings and Search for `Python Interpreter`
2. Select `Project: NarrativeIntelligence` - `Python Interpreter`
3. Click on **Add Interpreter** - **On SSH**

A new window shows up.
Create a new SSH connection:

1. Select **New Target: SSH**
2. SSH Connection **New**
3. Insert **Hostname** `SERVER-ADDR`
4. Insert **Username** `pubpharm`
5. Click on **Next**

A connection test is conducted…
Click on **Next** until page 4/4 is visible.

Select to connect to a `Conda Environment` on the left
If the executable (on remote) is not automatically found, insert the path to the conda env.
The path should look something like this: `/home/pubpharm/anaconda3/bin/conda`.

In the dropdown **Use existing environment** select `narraint-dev`.

Create synchronization for remote and local project folders:
1. Click on *Edit Sync Folder* (Icon on the far Right of the text element)
2. Navigate to local Project path on the left `/path/to/NarrativeIntelligence`
3. Navigate to remote Project path on the Right `/home/pubpharm/dev/NarrativeIntelligence`
4. Activate `Automatically upload Project files to the server`
5. Click on **Create**

Now, the Settings window can be closed.
To upload the project, right-click on **NarrativeIntelligence** in the project structure on the left, 
hover over **Deployment** (second last entry), and click on **Upload to pubpharm@SERVER-ADDR**

The synchronization may take a while…

> **Note** that the automatic synchronization runs only if a file is changed locally (in the IDE).
> It does not work, when the repository is pulled.
> You have to sync the changes manually, e.g., by repeating the sync process mentioned above.

> The loading bar on the bottom of the IDE indicates the upload of any change

## Remote-Development-4:: Configure the service

All configuration lives inside the `NarrativeIntelligence/config` directory. 
The `*.prod.json` files show the structure of the corresponding configuration file. 
Copy the example file and remove the `.example` from the filename. 
To run the service, only `backend.json` is required. 
The database can be configured with the file `backend.json` and using environment variables. 
The environment variables are favoured over the json-configuration.

Navigate to the project's root folder and execute the following commands to create the backend configuration.
```bash
cd config
cp backend.prod.json backend.json
```

Next, configure the database connection in `backend.json`.
For example, using nano (`nano backend.json`) or any other text editor.

Insert the postgres username and password to get access to the fidpharmazie database.
```json
{
  "use_SQLite": false,
  "SQLite_path": "sqlitebase.db",
  "POSTGRES_DB": "fidpharmazie-dev",
  "POSTGRES_HOST": "127.0.0.1",
  "POSTGRES_PORT": "5432",
  "POSTGRES_USER": "pubpharm",
  "POSTGRES_PW": "POSTGRES_PASSWORD",
  "POSTGRES_SCHEMA": "public"
}
```

As a last step, mark each `src` folder as `Sources Root`.
Therefore, right-click on the `NarrativeIntelligence/src` folder and select `Mark directory as` - `Sources Root`.
Repeat the process for the source folders in `lib/NarrativeAnnotation/src` and `lib/KGExtractionToolbox/src`.

## Remote-Development-5: Download external dependencies

The following steps are required only on the remote server.
Therefore, execute the commands in a SSH session.

First, activate the conda environment:
```bash
conda activate narraint-dev
```

Install the necessary Python requirements including those of the submodules.
```bash
cd ~/dev/NarrativeIntelligence
python -m pip install -r requirements.txt \
                      -r lib/NarrativeAnnotation/requirements.txt \
                      -r lib/KGExtractionToolbox/requirements.txt
```

Download additional data (project-local).
```bash
cd lib/NarrativeAnnotation/
bash download_data.sh
```

Now, the external dependencies are loaded.
You can close the SSH session.

## Remote-Development-6: Create Django Executable in PyCharm

Now, you are ready create a run config for the service application.
But first, the PyCharm settings have to be adjusted for Django: 

1. Open Settings and search for `Django`
2. Navigate to `Languages & Frameworks` - `Django`
3. Enable **Django Support**
4. Insert (local!) **Django Project root:** `/path/to/NarrativeIntelligence/src/narraint/frontend`
5. Insert **Settings** `frontend/settings/dev.py`
6. Insert **Manage script:** `manage.py`
7. Insert **Folder pattern to track files:** `migrations`
8. Click on **Ok** and close the window

Open run configurations and configure remote interpreter for new Django application (top Right):

1. Click on **Edit Configurations...**
2. Create new `Django Server` run configuration by clicking on **+** on the left (Add new configuration)
3. Select remote Conda Interpreter (`narraint-dev`)
4. Insert host `localhost`
5. Append the **Environment Variables:** with `PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=frontend.settings.dev`
6. Click on **Apply** and close the window

Now, the Django Server can be started.

### Activate SSH Port Forwarding for the NarrativeService

To connect to the local service, the last step is to forward the required port.
By default, the port is set to `8000`.
To change it, the corresponding parameter `Port` needs to be changed in the run configuration. (Next to `localhost`)

Start a terminal and execute the following command:
```bash
ssh -L 8000:localhost:8000 pubpharm@<SERVER-ADDR>
```

> **Note** that those connections need to be alive when the service runs.

### Finally: Start the Narrative Service

If everything works correctly, the server starts (after clicking on the green triangle on the top left).
When the initialization is finished the IP address will show up to access the service.
Open the ip address with the browser.

Congratulations, you have done it.

## Remote-Development-7: Create Unit-Tests Executables in PyCharm

The service comes with a bunch of unit tests to ensure that it works as expected.
Each set of tests is located as a subdirectory of the source folders, namely `nitests`, `narranttests`, and `kgtests`.

To run on of the tests, create a new run configuration (as for step 6).
1. Select the run-config type `Python tests` - `Autodetect`
2. Select the remote interpreter `narraint-dev`
3. Choose to execute a `Script` 
4. Enter the **Script path** to the test root, e.g., `/path/to/NarrativeIntelligence/src/nitests`
5. Enter the same path at **Working directory**
6. Click on **Apply** and close the window

Select the freshly created run-config and execute it.
The tests should be detected automatically.


# Mac Development (Apple Silicon)
Apple Silicon has LibreSSL installed, however the URL package expects OpenSSL to be installed.
That is why we need to downgrade the requirement to a lower version.
```
pip install urllib3==1.26.7
```

The `psycopg2-binary` can not be installed with the expected version (2.9.1).
Instead, the version needs to be higher (2.9.3):
```
pip install psycopg2-binary==2.9.3
```