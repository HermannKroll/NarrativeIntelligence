#!/bin/bash
cd $1
source /home/kroll/anaconda3/bin/activate openie6
python run.py --mode splitpredict --inp $2 --out $3 --rescoring --task oie --gpus 1 --oie_model models/oie_model/epoch=14_eval_acc=0.551_v0.ckpt --conj_model models/conj_model/epoch=28_eval_acc=0.854.ckpt --rescore_model models/rescore_model --num_extractions 5