#!/bin/bash
# This tool creates an archive containing the compressed Docker image and the required docker-compose.yml file to start
# the stack

MODEL_DIR=/home/kroll/tools/tagger/TaggerOne-0.2.1/models

if [ ! -d TaggerOne/models ]; then
  echo "Copying TaggerOne models ..."
  cp -r ${MODEL_DIR} TaggerOne/.
fi

if [ ! -f GNormPlusJava.zip ]; then
  echo "Downloading GNormPlus ..."
  wget https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/tmTools/download/GNormPlus/GNormPlusJava.zip
fi

if [ ! -f DNorm-0.0.7.tgz ]; then
  echo "Downloading DNorm ..."
  wget https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/tmTools/download/DNorm/DNorm-0.0.7.tgz
fi

if [ ! -f tmChemM1-0.0.2.tgz ]; then
  echo "Downloading tmChemM1 ..."
  wget https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/tmTools/download/tmChem/tmChemM1-0.0.2.tgz
fi

if [ ! -f TaggerOne-0.2.1.tgz ]; then
  echo "Downloading TaggerOne ..."
  wget https://www.ncbi.nlm.nih.gov/research/bionlp/taggerone/TaggerOne-0.2.1.tgz
fi


echo "Building Docker image ..."

cd ..

docker image build -t narraint:latest .


echo "Saving Docker image ..."

cd docker

mkdir -p build

docker save narraint:latest | gzip >build/narraint-image.tar.gz


echo "Building archive ..."

tar -zcvf build/narraint-deploy.tar.gz narraint-image.tar.gz docker-compose.ymp
