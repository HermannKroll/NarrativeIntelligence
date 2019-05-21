# PubMedSnorkel
## Getting Started
Download ctd data for labeling training and test data. This download recommends 3GB of free disk space.

```
.\download_ctd_data.sh
```

## Preprocessing for PubMedCentral

If you want to use the full text of the PubMedCentral documents, you can use the ``preprocessing`` package to create a document collection with tagged chemicals, diseases, genes and species in the PubTator format.

You need the following requirements to use the package:

- TaggerOne v0.2.1 with a model for recognizing chemicals and diseases (e.g. model_BC5CDRJ)
- GNormPlusJava
- Python 3.6.x with ``lxml`` 4.3.3

The package also requires the PubMedCentral Open Access Document Collection in the ``xml`` format.

1. Install the Python requirements:

       pip install -r requirements.txt
    
1. Copy the ``config.example.json`` to ``config.json`` and adjust the settings 

1. Start the pipeline using

       python preprocess.py ids.txt tagged_documents.txt

## Enable GPU Support for Training (PyTorch)
First switch to conda prompt in env

Find your installed Cuda Version 
	cat /usr/local/cuda/version.txt

Coda Version 9

        conda install pytorch torchvision cudatoolkit=9.0 -c pytorch  

Cuda Version 10:

        conda install pytorch torchvision cudatoolkit=10.0 -c pytorch   
