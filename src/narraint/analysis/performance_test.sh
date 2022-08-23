#!/bin/bash
export PYTHONPATH="$HOME/narint/"
for tagtype in "DF DR E PF";
do
  for n in 1 2 3;
  do
    echo "cleaning workdir and sqlbase"
    rm -r ~/workdir
    rm /home/jan/sqlite.db
    echo "running ${n}th test for tagtype ${tagtype}"
    /home/jan/.conda/envs/narint/bin/python3.7 -u /home/jan/narint/narraint/preprocessing/preprocess.py /home/jan/pubmed_10k_sample/sample.txt /dev/null -t $tagtype --loglevel DEBUG -c TOTEST --composite --workdir /home/jan/workdir
    echo "copy logfile "
    cp ~/workdir/log/preprocessing.log ~/perftest/"${tagtype}_${n}.log"

  done
done