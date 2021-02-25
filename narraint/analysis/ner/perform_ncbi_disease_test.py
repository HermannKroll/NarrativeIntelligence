import os
from collections import defaultdict

import logging

from narraint.config import DATA_DIR
from narraint.pubtator.regex import TAG_LINE_NORMAL

NCBI_DISEAE_TEST_DIR = os.path.join(DATA_DIR, "extraction/ncbi_disease")

NCBI_DISEASE_TEST_FILE = os.path.join(NCBI_DISEAE_TEST_DIR, "NCBItestset_corpus.txt")
NCBI_DISEASE_TAGGED_FILE = os.path.join(NCBI_DISEAE_TEST_DIR, 'ncbi_documents.tagged.pubtator')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    correct_diseases = defaultdict(set)
    with open(NCBI_DISEASE_TEST_FILE, 'rt') as f:
        content = f.read()
    tags = [t for t in TAG_LINE_NORMAL.findall(content)]
    count_omim_tags = 0
    for t in tags:
        # consider mesh descriptors only
        if not t[5].startswith('D'):
            count_omim_tags += 1
            continue
        # composite tag mention - allow all tags
        if '|' in t[5]:
            for ent_id in t[5].split('|'):
                correct_diseases[int(t[0])].add((int(t[1]), int(t[2]), ent_id))
        else:
            correct_diseases[int(t[0])].add((int(t[1]), int(t[2]), t[5]))

    print(f'{count_omim_tags} of {count_omim_tags + len(tags)} are ignored (omim is not supported)')

    tagged_diseases = defaultdict(set)
    with open(NCBI_DISEASE_TAGGED_FILE, 'rt') as f:
        content = f.read()
    own_tags = [t for t in TAG_LINE_NORMAL.findall(content)]
    for t in own_tags:
        # consider mesh descriptors only
        tagged_diseases[int(t[0])].add((int(t[1]), int(t[2]), t[5][5:]))

    count_correct_extractions = 0
    count_wrong_extractions = 0
    for doc_id, tags in tagged_diseases.items():
        if doc_id in correct_diseases:
            for start, end, ent_id in tags:
                if (start, end, ent_id) in correct_diseases[doc_id] \
                        or (start + 1, end, ent_id) in correct_diseases[doc_id]:
                    count_correct_extractions += 1
                else:
                    count_wrong_extractions += 1
        else:
            count_wrong_extractions += len(tags)

    count_missing_extractions = 0
    for doc_id, correct_tags in correct_diseases.items():
        if doc_id in tagged_diseases:
            for start, end, ent_id in correct_tags:
                if (start, end, ent_id) not in tagged_diseases[doc_id] \
                        and (start - 1, end, ent_id) not in tagged_diseases[doc_id]:
                    count_missing_extractions += 1
                    print(f'tag missed: {doc_id} {start} {end} {ent_id}')
        else:
            count_missing_extractions += len(correct_tags)

    precision = count_correct_extractions / (count_correct_extractions + count_wrong_extractions)
    recall = count_correct_extractions / (count_correct_extractions + count_missing_extractions)
    f1 = (2 * precision * recall) / (precision + recall)
    logging.info(f'Precision: {precision}')
    logging.info(f'Recall: {recall}')
    logging.info(f'F1-measure: {f1} ')


if __name__ == "__main__":
    main()
