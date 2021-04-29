import argparse
import os
import json
import tempfile
from datetime import datetime
import logging

import shutil
from time import sleep

import spacy
import subprocess
from spacy.lang.en import English

from narraint.config import NLP_CONFIG
from narraint.extraction.extraction_utils import filter_document_sentences_without_tags
from narraint.extraction.openie.cleanload import OPENIE_TUPLE
from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents


def openie6_read_extractions(openie6_output):
    tuples = []
    doc_ids = set()
    nlp = spacy.load('en', disable=['parser', 'ner'])
    # open the input allenai open ie file
    with open(openie6_output, 'r') as f:
        # read all lines for a single doc
        doc_id, sentence_txt = 0, ""
        for line in f:
            try:
                if not line or line == '\n':
                    continue
                if not line.startswith('0.') and not line.startswith('1.'):
                    doc_id, sentence_txt = line.split('.', maxsplit=1)
                    doc_id = int(doc_id)
                    sentence_txt = sentence_txt.strip()
                else:
                    if not doc_id or not sentence_txt:
                        continue
                    confidence, extraction = line.strip().split(": (", maxsplit=1)
                    if extraction.count(';') < 2:
                        logging.info(f'Skip extraction because no object was found: {extraction}')
                    # split by ';'
                    subj_txt, pred_txt, obj_txt = extraction.split(';', maxsplit=2)
                    pred_lemma = ' '.join([token.lemma_ for token in nlp(pred_txt)])
                    ex_tuple = OPENIE_TUPLE(int(doc_id), subj_txt, pred_txt, pred_lemma, obj_txt, confidence, sentence_txt)
                    tuples.append(ex_tuple)
                doc_ids.add(doc_id)
            except ValueError:
                continue
    return tuples


def openie6_extract_tuples(openie6_output_file, extraction_output):
    logging.info('Converting OpenIE6 output...')
    tuples = openie6_read_extractions(openie6_output_file)

    with open(extraction_output, 'wt') as f:
        f.write('\n'.join(['\t'.join([str(x) for x in t]) for t in tuples]))


def openie6_convert_pubtator_to_openie6_input(doc2sentences, openie6_input):
    doc_size = len(doc2sentences)
    logging.info('Writing {} documents as OpenIE 6 input...'.format(doc_size))
    start_time = datetime.now()
    with open(openie6_input, 'wt') as f_out:
        for idx, (doc_id, sentences) in enumerate(doc2sentences.items()):
            for sent in sentences:
                f_out.write('{}. {}.\n'.format(doc_id, sent))
            print_progress_with_eta(f'Writing {doc_size} documents as OpenIE 6 input...', idx, doc_size, start_time)
    logging.info('Conversion finished')


def openie6_invoke_toolkit(openie6_dir, input_file, output_file):
    start = datetime.now()
    run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh")
    sp_args = ["/bin/bash", "-c", "{} {} {} {}".format(run_script, openie6_dir, input_file, output_file)]
    process = subprocess.Popen(sp_args, cwd=openie6_dir)
    start_time = datetime.now()
    logging.info('Waiting for OpenIE6 to terminate...')
    while process.poll() is None:
        sleep(1)


def run_openie6(input_file, output, config=NLP_CONFIG):
    # Read config
    with open(config) as f:
        conf = json.load(f)
        openie6_dir = conf["openie6"]
    logging.info('Init spacy nlp...')
    spacy_nlp = English()  # just the language with no model
    sentencizer = spacy_nlp.create_pipe("sentencizer")
    spacy_nlp.add_pipe(sentencizer)

    # Prepare files
    doc_count = count_documents(input_file)
    logging.info('{} documents counted'.format(doc_count))

    doc2sentences, doc2tags = filter_document_sentences_without_tags(doc_count, input_file, spacy_nlp)
    amount_files = len(doc2tags)

    openie6_input_file = f'{output}_pubtator'
    openie6_raw_extractions = f'{output}_extractions'
    if amount_files == 0:
        print('no files to process - stopping')
    else:
        start = datetime.now()
        # Process output
        openie6_convert_pubtator_to_openie6_input(doc2sentences, openie6_input_file)
        # invoke OpenIE 6
        openie6_invoke_toolkit(openie6_dir, openie6_input_file, openie6_raw_extractions)
        # extract tuples
        openie6_extract_tuples(openie6_raw_extractions, output)
        print(f'removing temp file: {openie6_input_file}')
        os.remove(openie6_input_file)
        print(f'removing temp file: {openie6_raw_extractions}')
        os.remove(openie6_raw_extractions)
        print(" done in {}".format(datetime.now() - start))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="PubTator input file (with tags)")
    parser.add_argument("output", help="OpenIE results will be stored here")
    parser.add_argument("--config", default=NLP_CONFIG)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    run_openie6(args.input, args.output, args.config)


if __name__ == "__main__":
    main()
