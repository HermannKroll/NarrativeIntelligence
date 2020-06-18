import argparse
import os
import tempfile
from datetime import datetime
import logging

import spacy

from narraint.backend.export import export
from narraint.extraction.openie.cleanload import OPENIE_TUPLE
from narraint.extraction.pipeline import retrieve_document_ids_to_process
from narraint.progress import print_progress_with_eta
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS


def split_allenai_arguments_to_single_arguments(text):
    # 'SpatialArgument(on six maturity-onset diabetic subjects,List([59, 98))); TemporalArgument(during successive periods of therapy with phenformin, metformin, and glibenclamide,List([99, 181)))'
    # split in two arguments
    return text.split('); ')


def convert_allenai_argument_to_text(argument):
    # 'Relation(have been performed,List([39, 58)))' -> have been performed
    # 'SpatialArgument(on six maturity-onset diabetic subjects,List([59, 98)))'->on six maturity-onset diabetic subjects
    if not argument:
        return []
    return argument.split('(')[1].split(',List')[0]


def read_allenai_openie_input(openie4_file):
    tuples = []
    doc_ids = set()
    nlp = spacy.load('en', disable=['parser', 'ner'])
    # open the input allenai open ie file
    with open(openie4_file, 'r') as f:
        # read all lines for a single doc
        for line in f:
            comps = line.strip().split("\t")
            if len(comps) != 6:
                raise ValueError('Components are longer than 6 elements: {}'.format(comps))
            #print(comps)
            if not comps[3].startswith('Relation'):
                raise ValueError('No predicate found in components: {}'.format(comps))
            pred = convert_allenai_argument_to_text(comps[3])
            pred_lemma = ' '.join([token.lemma_ for token in nlp(pred)])
            conf = comps[0]
            # subjects are in front of the predicate
            subjects = split_allenai_arguments_to_single_arguments(comps[2])
            # objects are behind the predicate
            objects = split_allenai_arguments_to_single_arguments(comps[4])
            # last element is the document + sentence
            doc_id, sent = comps[-1].split('.', maxsplit=1)
            for sub in subjects:
                for obj in objects:
                    if not sub or not obj:
                        continue
                    sub_t = convert_allenai_argument_to_text(sub)
                    obj_t = convert_allenai_argument_to_text(obj)
                    #print('{}: ({}, {}, {}, {})'.format(doc_id, sub_t, pred, pred_lemma, obj_t))
                    tuple = OPENIE_TUPLE(int(doc_id), sub_t, pred, pred_lemma, obj_t, conf, sent)
                    tuples.append(tuple)
                    doc_ids.add(doc_id)
    return doc_ids, tuples



def convert_pubtator_to_openie4_input(document_ids, pubtator_file, openie4_file):
    doc_size = len(document_ids)
    logging.info('Converting {} documents'.format(doc_size))
    start_time = datetime.now()
    with open(openie4_file, 'wt') as f_out:
        for idx, pubtator_content in enumerate(read_pubtator_documents(pubtator_file)):
            doc_id, title, abstract = CONTENT_ID_TIT_ABS.match(pubtator_content).group(1, 2, 3)

            f_out.write('{}. {}.\n'.format(doc_id, title))
            for sent in abstract.split('. '):
                f_out.write('{}. {}.\n'.format(doc_id, sent))

            print_progress_with_eta('filtering documents...', idx, doc_size, start_time)

    logging.info('Conversion finished')



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idfile", help="Document ID file (documents must be in database)")
    parser.add_argument("output", help="OpenIE results will be stored here")
    parser.add_argument("-c", "--collection", help="Name of the given document collection")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    time_start = datetime.now()
    working_dir = tempfile.mkdtemp()
    document_export_file = os.path.join(working_dir, 'document_export.pubtator')
    openie_input_dir = os.path.join(working_dir, 'openie')
    openie_filelist_file = os.path.join(working_dir, 'openie_filelist.txt')
    openie_output_file = os.path.join(working_dir, 'openie.output')

    if not os.path.exists(working_dir):
        os.mkdir(working_dir)
    if not os.path.exists(openie_input_dir):
        os.mkdir(openie_input_dir)

    logging.info('Process will work in: {}'.format(working_dir))
    # first get a list of all document ids which have to be processed
    ids_to_process = retrieve_document_ids_to_process(args.idfile, args.collection)
    # export them with their tags
    export(document_export_file, None, document_ids=ids_to_process, collection="PubMed", content=True)
    time_exported = datetime.now()
    logging.info('Documents exported in : {}s'.format(time_exported - time_start))
    convert_pubtator_to_openie4_input(ids_to_process, document_export_file, args.output)


if __name__ == "__main__":
    main()
