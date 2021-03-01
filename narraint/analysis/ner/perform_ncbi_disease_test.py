import itertools
import os
import csv
from collections import defaultdict

import logging

from narraint.config import DATA_DIR, PREPROCESS_CONFIG
from narraint.preprocessing.config import Config
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.disease import DiseaseTagger
from narraint.preprocessing.tagging.vocabularies import expand_vocabulary_term
from narraint.pubtator.document import parse_tag_list, TaggedEntity, TaggedDocument
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import TAG_LINE_NORMAL
from nitests.util import create_test_kwargs  # meh
from matplotlib import pyplot as plt

NCBI_DISEAE_TEST_DIR = os.path.join(DATA_DIR, "NER/ncbi_disease")

NCBI_DISEASE_TEST_FILE = os.path.join(NCBI_DISEAE_TEST_DIR, "NCBItestset_corpus.txt")
NCBI_DISEASE_TAGGED_FILE = os.path.join(NCBI_DISEAE_TEST_DIR, 'ncbi_documents_dev.tagged.pubtator')
TAGGERONE_VOCAB = os.path.join(NCBI_DISEAE_TEST_DIR, 'taggerone/CTD_diseases.tsv')

use_taggerone_vocab = False
substring_matching = True


def create_taggerone_vocab_dictagger():
    tagger = DiseaseTagger(config=Config(PREPROCESS_CONFIG))
    if use_taggerone_vocab:
        vocab = dict()
        with open(TAGGERONE_VOCAB, newline='') as f:
            vocab_reader = csv.reader(f, delimiter="\t")
            for row in vocab_reader:
                if row[0].strip()[0] == "#":
                    continue
                if len(row[0]) < tagger.config.dict_min_full_tag_len:
                    continue
                names = [name for n in [row[0]]+row[7].split("|") for name in expand_vocabulary_term(n.lower()) ]
                desc = {d for s in [row[1].split("|"), row[2].split("|")] for d in s if d}
                #desc = {row[1]}
                for name in names:
                    if name not in vocab:
                        vocab[name] = set()
                    vocab[name] |= desc

        tagger.desc_by_term = vocab
    else:
        tagger.prepare()
    return tagger


def tags_from_file(input_file:str, tagger:DictTagger):
    for content in read_pubtator_documents(input_file):
        try:
            doc = TaggedDocument(content, ignore_tags=True)
        except:
            logging.debug(f"Skipping document, unable to parse")
            continue
        if doc.title and doc.abstract:
            tagger.tag_doc(doc)
            doc.clean_tags()
            yield from doc.tags


def run_test(s_e_tolerance: int=1):
    start_end_tolerance = s_e_tolerance
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    tagger = create_taggerone_vocab_dictagger()

    documents = dict()
    correct_diseases = defaultdict(set)
    with open(NCBI_DISEASE_TEST_FILE, 'rt') as f:
        content = f.read()
    tags = [t for t in TAG_LINE_NORMAL.findall(content)]
    count_omim_tags = 0
    for t in tags:
        # consider mesh descriptors only
        tag = TaggedEntity(document=t[0], start=t[1], end=t[2], text=t[3], ent_type="Disease", ent_id=t[5])
        if not tag.ent_id.startswith('D') and not use_taggerone_vocab:
            count_omim_tags += 1
            continue
        # composite tag mention - allow all tags
        if '|' in tag.ent_id:
            for ent_id in tag.ent_id.split('|'):
                correct_diseases[int(tag.document)].add(
                    TaggedEntity(document=tag.document, start=tag.start, end=tag.end, text=tag.text, ent_type=tag.ent_type,
                                 ent_id=ent_id))
        else:
            correct_diseases[int(tag.document)].add(tag)

    logging.debug(f'{count_omim_tags} of {count_omim_tags + len(tags)} are ignored (omim is not supported)')

    tagged_diseases = defaultdict(set)
    # Read tags from file
    #with open(NCBI_DISEASE_TAGGED_FILE, 'rt') as f:
    #    content = f.read()
    #own_tags = parse_tag_list(content)

    # Tag on the fly
    own_tags = tags_from_file(NCBI_DISEASE_TEST_FILE, tagger)
    for t in own_tags:
        if not t.ent_id[0:4]=="OMIM":
         t.ent_id = t.ent_id[5:]
         tagged_diseases[int(t.document)].add(t)



    count_correct_extractions = 0
    count_wrong_extractions = 0
    for doc_id, tags in tagged_diseases.items():
        if doc_id in correct_diseases:
            correct_list = [(t.start, t.end, t.ent_id) for t in correct_diseases[doc_id]]
            for tag in tags:
                matched = False
                if not substring_matching:
                    for x,y in itertools.product(range(-start_end_tolerance,start_end_tolerance), range(-start_end_tolerance,start_end_tolerance)):
                        if (tag.start + x, tag.end+y, tag.ent_id) in correct_list:
                            count_correct_extractions += 1
                            matched = True
                            break
                    else:
                        matched = False
                else:
                    for compare_tag in correct_diseases[doc_id]:
                        if tag.ent_id == compare_tag.ent_id and compare_tag.start <= tag.start+1 and tag.end <= compare_tag.end:
                            if(compare_tag.end-compare_tag.start-1>tag.end-tag.start):
                                logging.debug(f"Subtag:<{str(tag)[:-1]}> for <{str(compare_tag)[:-1]}>")
                            count_correct_extractions += 1
                            matched = True
                            break
                    else:
                        matched = False
                if not matched:
                    count_wrong_extractions += 1
                    logging.debug(f"wrong tag: {tag}"[:-1])
        else:
            count_wrong_extractions += len(tags)

    count_missing_extractions = 0
    for doc_id, correct_tags in correct_diseases.items():
        if doc_id in tagged_diseases:
            tagged_list = [(t.start, t.end, t.ent_id) for t in tagged_diseases[doc_id]]
            for tag in correct_tags:
                matched = False
                if not substring_matching:
                    for x, y in itertools.product(range(-start_end_tolerance,start_end_tolerance),
                                                  range(-start_end_tolerance,start_end_tolerance)):
                        if (tag.start + x, tag.end + y, tag.ent_id) in tagged_list:
                            matched = True
                            break
                    else:
                        matched = False
                else:
                    for compare_tag in tagged_list:
                        if tag.ent_id == compare_tag[-1] and compare_tag[0]+1 >= tag.start and tag.end >= compare_tag[1]:
                            matched=True
                            break
                    else:
                        matched = False


                if not matched:
                    count_missing_extractions += 1
                    logging.debug(f'tag missed: {tag}'[:-1])
        else:
            count_missing_extractions += len(correct_tags)

    precision = count_correct_extractions / (count_correct_extractions + count_wrong_extractions)
    recall = count_correct_extractions / (count_correct_extractions + count_missing_extractions)
    f1 = (2 * precision * recall) / (precision + recall) if (precision+recall)>0 else 0
    logging.info(f'Precision: {precision}')
    logging.info(f'Recall: {recall}')
    logging.info(f'F1-measure: {f1} ')
    return(precision, recall, f1)


def draw_diagram():
    n = 3
    result = [[i-1, *run_test(i)] for i in range(1,n)]
    print(result)
    result = [l for l in zip(*result)]
    plt.xlabel("Toleranz für Start/Ende")
    ax = plt.subplot(111)
    ax.plot(result[0], result[1], label="precision")
    ax.plot(result[0], result[2], label="recall")
    ax.plot(result[0], result[3], label="f-measure")
    ax.legend()
    plt.show()


def run_single_test():
    run_test(1)

def compare_our_taggerone():
    global use_taggerone_vocab
    use_taggerone_vocab = False
    run_test(1)


def main():
    run_single_test()


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    main()
