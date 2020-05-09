#!/bin/bash

cd $1
java -Xms48g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLP -threads 28 -annotators tokenize,ssplit,pos,lemma,parse -outputFormat json -outputDirectory $2 --filelist $3