import argparse
import json
import os
import tempfile
from datetime import datetime
import logging

from narraint.backend import enttypes
from narraint.backend.database import Session
from narraint.backend.export import export
from narraint.backend.models import DocProcessedByOpenIE
from narraint.openie.main import run_openie, process_output
from narraint.progress import print_progress_with_eta
from narraint.config import OPENIE_CONFIG
from narraint.pubtator.document import TaggedDocument
from narraint.pubtator.extract import read_pubtator_documents


def retrieve_document_ids_to_process(idfile, document_collection):
    logging.info('Reading id file: {}'.format(idfile))
    with open(idfile, 'r') as f:
        document_ids = set([int(line.strip()) for line in f])
    logging.info('{} ids retrieved from id file..'.format(len(document_ids)))

    logging.info('Retrieving already processed document ids from database...')
    session = Session.get()
    q = session.query(DocProcessedByOpenIE.document_id).filter_by(document_collection=document_collection)
    processed_ids = set()
    for r in session.execute(q):
        processed_ids.add(r[0])

    logging.info('{} document ids are in the database'.format(len(processed_ids)))
    missing_ids = document_ids.difference(processed_ids)
    logging.info('{} ids have already be processed and will be skipped'.format(len(document_ids)-len(missing_ids)))
    logging.info('{} remaining document ids to process...'.format(len(missing_ids)))
    return missing_ids


def filter_document_sentences_without_tags(document_ids, input_file, output_dir, openie_filelist):
    doc_size = len(document_ids)
    logging.info('Filtering {} documents (keep only document sentences with tags)'.format(doc_size))
    amount_skipped_files = 0
    amount_files = 0
    openie_files = []
    start_time = datetime.now()
    for idx, pubtator_content in enumerate(read_pubtator_documents(input_file)):
        tagged_doc = TaggedDocument(pubtator_content)
        doc_id = tagged_doc.id
        filtered_content = []
        for sent, ent_ids in tagged_doc.entities_by_sentence.items():
            if len(ent_ids) > 1:  # at minimum two tags must be included in this sentence
                filtered_content.append(tagged_doc.sentence_by_id[sent].text)

        # skip empty documents
        if not filtered_content:
            continue
        # write filtered document
        o_file = os.path.join(output_dir, '{}.txt'.format(doc_id))
        openie_files.append(o_file)
        with open(o_file, 'w') as f_out:
            f_out.write('. '.join(filtered_content))

        print_progress_with_eta('filtering documents...', idx, doc_size, start_time)

    logging.info('{} files need to be processed. {} files skipped.'.format(amount_files, amount_skipped_files))
    with open(openie_filelist, "w") as f:
        f.write("\n".join(openie_files))
    return len(openie_filelist)


def mark_document_as_processed_by_openie(document_ids, document_collection):
    logging.info('Inserting processed document ids into database...')
    doc_inserts = []
    for doc_id in document_ids:
        doc_inserts.append(dict(document_id=doc_id, document_collection=document_collection))
    session = Session.get()
    session.bulk_insert_mappings(DocProcessedByOpenIE, doc_inserts)
    session.commit()
    logging.info('{} document ids have been inserted')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idfile", help="Document ID file (documents must be in database)")
    parser.add_argument("output", help="OpenIE results will be stored here")
    parser.add_argument("-c", "--collection", help="Name of the given document collection")
    parser.add_argument("--conf", default=OPENIE_CONFIG)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    # Read config
    with open(args.conf) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]

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
    export(document_export_file, enttypes.ALL, document_ids=ids_to_process, collection=args.collection, content=True)
    # now filter these documents
    amount_openie_docs = filter_document_sentences_without_tags(ids_to_process, document_export_file, openie_input_dir,
                                                                openie_filelist_file)
    # run openie
    if amount_openie_docs == 0:
        logging.info('No files to process for OpenIE - stopping')
    else:
        run_openie(core_nlp_dir, openie_output_file, openie_filelist_file)
        logging.info("Processing output ...")
        start = datetime.now()
        # Process output
        process_output(openie_output_file, args.output)
        logging.info("Done in {}".format(datetime.now() - start))

    # add document as processed to database
    # mark_document_as_processed_by_openie(ids_to_process, args.collection)


if __name__ == "__main__":
    main()
