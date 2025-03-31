# Narrative Service Development Setup
This document describes the setup of a PyCharm IDE to develop on the Narrative Service.

## System Requirements

The Narrative Service requires a Linux-like OS to work properly.
It is because the implementation relies on certain Python libraries that work only on this OS.
To be OS-independent, a simple solution is to develop over SSH.

The following steps describe how to set up the PyCharm Professional IDE for SSH development.

*tl;dr, the following things are required:*
- Linux server (to run the service)
- PyCharm Professional (on any OS)
- SSH access to the dev server


- server user `pubpharm`
- postgres database `fidpharmazie`

## References:
- [PyCharm SSH Interpreter](https://www.jetbrains.com/help/pycharm/configuring-remote-interpreters-via-ssh.html)
- [PyCharm Django Setup](https://www.jetbrains.com/help/pycharm/creating-and-running-your-first-django-project.html)
- [Miniconda Docs](https://www.anaconda.com/docs/getting-started/miniconda/install#macos-linux-installation)
- [StackOverflow](https://stackoverflow.com/a/876565/23125650) - Copy postgres production databases 
## 0. Prerequisites

Since the development requires an active database connection, it needs to be initialized beforehand.
It is recommended to not use the production database for development, instead, create a copy of it.

The following command assumes, that a production database with the name `fidpharmazie` and the owner `pubpharm` exists (as created in with [Service-Readme](README_Service.md)).
It creates a new database with the name `fidpharmazie-dev`, owned by `pubpharm`, and using `fidpharmazie` as template.

> **Note** that the command needs to be executed as postgres user!

```bash
su postgres
createdb -O pubpharm -T fidpharmazie fidpharmazie-dev
exit
```

> It might be the case that active connections of the production database prevent the execution of `createdb`.
> If this is the case wait a few minutes or disconnect each active connection before executing the command again by
> running the following SQL code in the `isql` environment:

```sql
SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity 
WHERE pg_stat_activity.datname = 'fidpharmazie' AND pid <> pg_backend_pid();
```

> *If this step is skipped, the database name in config of step 4. needs to be changed back to* `fidpharmazie`

## 1. Create Python Virtual Environment

For the first step, connect to the remote server with a SSH session and login into the pubpharm user.
Download the latest version of miniconda. (If not already existent)

```bash
cd ~
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
```

Install miniconda.

```bash
bash ~/Miniconda3-latest-Linux-x86_64.sh
```

Proceed with the installation.
The default installation path `/home/pubpharm/miniconda3` should be sufficient.
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
The Narrative Service is based on Python version 3.8.

```bash
conda create -n narraint-dev python=3.8
```

Last, activate the newly created environment `narraint-dev`.

```bash
conda activate narraint-dev
```

## 2. Narrative Service Setup (Remote)

Now, create the directory on the server where the project should be live.
The project does not need to be cloned since we deploy it later from the local setup.

```bash
mkdir /home/pubpharm/dev/NarrativeIntelligence
```

## 3. Narrative Service Setup (Local)

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
The path should look something like this: `/home/pubpharm/miniconda3/bin/conda`.

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

## 4. Configure the service

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

## 5. Download external dependencies

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

## 6. Create Django Executable in PyCharm

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
3. Select remote Conda Interpreter (narraint-dev)
4. Insert host `localhost`
5. Append the **Environment Variables:** with `PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=frontend.settings.dev`
6. Click on **Apply** and close the window

Now, the Django Server can be started.

### Activate SSH Port Forwarding

To connect to the local service, the last step is to forward the required port.
By default, the port is set to `8000`.
To change it, the corresponding parameter `Port` needs to be changed in the run configuration. (Next to `localhost`)

Start a terminal and execute the following command:
```bash
ssh -L 8000:localhost:8000 pubpharm@<SERVER-ADDR>
```

> **Note** that this connection needs to be alive to access the service.

### Finally: Start the Narrative Service

If everything works correctly, the server starts (after clicking on the green triangle on the top left).
When the initialization is finished the IP address will show up to access the service.
Open the ip address with the browser.

Congratulations, you have done it.

## 7. Create Unit-Tests Executables in PyCharm

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

```
pip install urllib3==1.26.7
```