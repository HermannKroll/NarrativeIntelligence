#!/bin/bash

cd $1
java -Xms48g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLP -threads 30 -annotators "tokenize,ssplit,pos,lemma,depparse" -outputFormat json -outputDirectory $2 --filelist $3