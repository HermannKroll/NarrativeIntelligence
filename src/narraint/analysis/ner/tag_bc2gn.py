import os

import csv

import logging

from narraint import tools
from narraint.analysis.ner.perform_ncbi_disease_test import tags_from_file
from narraint.config import PREPROCESS_CONFIG, DATA_DIR
from narraint.preprocessing.config import Config
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.disease import DiseaseTagger
from narraint.preprocessing.tagging.vocabularies import expand_vocabulary_term

STOPWORD_LIST = tools.proj_rel_path("data/bc2gn_stopwords.txt")
BC2GN_DIR = os.path.join(DATA_DIR, "NER/biocreative2normalization/")
BC2GN_VOCAB = os.path.join(BC2GN_DIR, "entrezGeneLexicon.list")
BC2GN_PUTATOR = "/home/jan/bc2GNtest.pubtator" #"/home/jan/12065586.txt"
output = "/home/jan/bc2GNtest5.pubtator.tagged"

Config.dict_min_full_tag_len=5


def create_bc2gn_vocab_dictagger():
    tagger = DiseaseTagger(config=Config(PREPROCESS_CONFIG))
    logging.debug("reading stopwords...")
    with open(STOPWORD_LIST) as f:
        stopwords = {s[:-1] for s in f.readlines() if not s[0] == "#"}
    #stopwords = {}
    vocab = {}
    logging.debug("building vocab...")
    with open(BC2GN_VOCAB) as f:
        vocab_reader = csv.reader(f, delimiter="\t")
        for row in vocab_reader:
            for name in row[1:]:
                name = name.lower()
                if name in stopwords:
                    pass
                    continue
                for n in expand_vocabulary_term(name):
                    if n not in vocab:
                        vocab[n] = set()
                    if n in stopwords:
                        pass
                        continue
                    vocab[n] |= {row[0]}

    vocab = {k: v for k, v in vocab.items() if len(v) ==1}
    tagger.desc_by_term = vocab
    return tagger


def main():
    tagger = create_bc2gn_vocab_dictagger()
    logging.debug("tagging...")
    with open(output, "w+") as out:
        for tag in tags_from_file(BC2GN_PUTATOR, tagger):
            out.write(f"{tag.document}\t{tag.ent_id}\t{tag.text}\n")


if __name__ == '__main__':
    logging.basicConfig(level="DEBUG")
    main()