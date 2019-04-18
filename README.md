# PubMedSnorkel
## Getting Started (download ctd data)
```
.\download_ctd_data.sh
```

## Preprocessing for PubMedCentral

If you want to use the full text of the PubMedCentral documents, you can use the ``preprocessing`` package to create a document collection with tagged chemicals, diseases, genes and species in the PubTator format.

You need the following requirements to use the package:

- TaggerOne v0.2.1
- GNormPlusJava
- Ab3P v1.5 
- Python 3.6.x with ``lxml`` 4.3.3

The package also requires the PubMedCentral Open Access Document Collection in the ``xml`` format.

Install the Python requirements:

    pip install -r requirements.txt
    
At first, you need to collect and merge the desired documents into a PubTator format.
List all the PubMedCentral ids (PMCID) in a text file, one PMCID per line each.
    
    python collect.py -o pubtator.txt idfile.txt /path/to/pmc_files