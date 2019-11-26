#!/bin/bash

N=$1
COLLECTION=$2
DATA=$3

mkdir -p ${DATA}/batches
mkdir -p ${DATA}/logs
mkdir -p ${DATA}/out

python3 batch.py --files ${N} ${COLLECTION} ${DATA}/batches

FILES=${DATA}/batches/batch*.txt
for f in ${FILES}
do
  echo "Starting $f ..."
  NAME=$(basename ${f})
  NAME=${NAME%.txt}
  echo "screen -dmS ${NAME} bash -c \"python3 nlp.py --out ${DATA}/out/${NAME} ${f} 2>&1 | tee -a ${DATA}/logs/${NAME}.log\""
  screen -dmS ${NAME} bash -c "python3 nlp.py --out ${DATA}/out/${NAME} ${f} 2>&1 | tee -a ${DATA}/logs/${NAME}.log"
done