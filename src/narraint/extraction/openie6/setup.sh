#!/bin/bash
# see https://github.com/dair-iitd/openie6
conda create -n openie6 python=3.6
conda activate openie6
pip install -r requirements.txt
python -m nltk.downloader stopwords
python -m nltk.downloader punkt

