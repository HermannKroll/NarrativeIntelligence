import os
import csv

from narraint.preprocessing.tagging.vocabularies import DrugTaggerVocabulary
from narraint.tools import  reverse_set_index
import narraint.config as cnf

def main():
    vocab_without_chembl = reverse_set_index(DrugTaggerVocabulary.create_drugbank_vocabulary_from_source())
    vocab_with_chembl = reverse_set_index(DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(use_chembl_synonyms=True))
    diff = {k: v -vocab_without_chembl[k] for k, v in vocab_with_chembl.items()}
    with open(os.path.join(cnf.TMP_DIR,"vocab_compare.csv"), "w+") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"')
        writer.writerow(["DB-ID", "synonyms_without_chembl", "synonyms_with_chembl", "diff"])
        for k,v in vocab_with_chembl.items():
            writer.writerow([k,"|".join(vocab_without_chembl[k]), "|".join(v), "|".join(diff[k])])

if __name__ == '__main__':
    main()
