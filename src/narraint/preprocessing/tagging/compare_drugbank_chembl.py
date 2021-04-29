import os
import csv

from narraint.entity.entityresolver import EntityResolver
from narraint.preprocessing.tagging.vocabularies import DrugTaggerVocabulary
from narraint.tools import  reverse_set_index
from narraint.entity.enttypes import DRUG
import narraint.config as cnf

def main():
    vocab_without_chembl = reverse_set_index(DrugTaggerVocabulary.create_drugbank_vocabulary_from_source())
    vocab_with_chembl = reverse_set_index(DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(use_chembl_synonyms=True))
    diff = {k: v -vocab_without_chembl[k] for k, v in vocab_with_chembl.items()}

    entres = EntityResolver.instance()

    with open(os.path.join(cnf.TMP_DIR,"vocab_compare.csv"), "w+") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"')
        writer.writerow(["DB-ID", "synonyms_without_chembl", "synonyms_with_chembl", "diff"])
        for k,v in diff.items():
            name = entres.get_name_for_var_ent_id(k,DRUG)
            writer.writerow([k, name, " | ".join(v)])

if __name__ == '__main__':
    main()
