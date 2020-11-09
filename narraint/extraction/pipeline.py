import argparse
import json
import os
import tempfile
from datetime import datetime
import logging
import shutil

from spacy.lang.en import English

from narraint.entity import enttypes
from narraint.backend.database import Session
from narraint.backend.export import export
from narraint.backend.models import DocProcessedByIE
from narraint.extraction.extraction_utils import filter_and_write_documents_to_tempdir
from narraint.extraction.openie.main import run_openie, process_output
from narraint.extraction.pathie.main import pathie_run_corenlp, pathie_process_corenlp_output
from narraint.extraction.versions import PATHIE_EXTRACTION, OPENIE_EXTRACTION
from narraint.config import OPENIE_CONFIG, PATHIE_CONFIG


def retrieve_document_ids_to_process(idfile, document_collection, extraction_type):

    logging.info('Reading id file: {}'.format(idfile))
    with open(idfile, 'r') as f:
        document_ids = set([int(line.strip()) for line in f])
    logging.info('{} ids retrieved from id file..'.format(len(document_ids)))
    logging.info('Retrieving already processed document ids from database...')
    session = Session.get()
    q = session.query(DocProcessedByIE.document_id)\
        .filter_by(document_collection=document_collection)\
        .filter_by(extraction_type=extraction_type)
    processed_ids = set()
    for r in session.execute(q):
        processed_ids.add(r[0])
    logging.info('{} document ids are in the database'.format(len(processed_ids)))
    missing_ids = document_ids.difference(processed_ids)
    logging.info('{} ids have already been processed and will be skipped'.format(len(document_ids)-len(missing_ids)))
    logging.info('{} remaining document ids to process...'.format(len(missing_ids)))
    return missing_ids


def mark_document_as_processed_by_ie(document_ids, document_collection, extraction_type):
    logging.info('Inserting processed document ids into database...')
    doc_inserts = []
    for doc_id in document_ids:
        doc_inserts.append(dict(document_id=doc_id,
                                document_collection=document_collection,
                                extraction_type=extraction_type))
    session = Session.get()
    session.bulk_insert_mappings(DocProcessedByIE, doc_inserts)
    session.commit()
    logging.info('{} document ids have been inserted')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idfile", help="Document ID file (documents must be in database)")
    parser.add_argument("output", help="OpenIE results will be stored here")
    parser.add_argument("extraction_type", help="OpenIE | PathIE")
    parser.add_argument("-c", "--collection", required=True, help="Name of the given document collection")
    parser.add_argument("--conf", help="OpenIE / PathIE Configuration file")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    if args.extraction_type not in [PATHIE_EXTRACTION, OPENIE_EXTRACTION]:
        raise argparse.ArgumentError('extraction type must either be {} or {}'.format(PATHIE_EXTRACTION, OPENIE_EXTRACTION))
    # Read config
    if args.conf:
        config_file = args.conf
    else:
        if args.extraction_type == PATHIE_EXTRACTION:
            config_file = PATHIE_CONFIG
        else:
            config_file = OPENIE_CONFIG
    with open(config_file) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]


    time_start = datetime.now()
    working_dir = tempfile.mkdtemp()
    document_export_file = os.path.join(working_dir, 'document_export.pubtator')
    ie_input_dir = os.path.join(working_dir, 'ie')
    ie_filelist_file = os.path.join(working_dir, 'ie_filelist.txt')
    ie_output_file = os.path.join(working_dir, 'ie.output')
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)
    if not os.path.exists(ie_input_dir):
        os.mkdir(ie_input_dir)

    logging.info('Process will work in: {}'.format(working_dir))
    # first get a list of all document ids which have to be processed
    ids_to_process = retrieve_document_ids_to_process(args.idfile, args.collection, args.extraction_type)
    # export them with their tags
    export(document_export_file, enttypes.ALL, document_ids=ids_to_process, collection=args.collection, content=True)
    time_exported = datetime.now()

    logging.info('Init spacy nlp...')
    spacy_nlp = English()  # just the language with no model
    sentencizer = spacy_nlp.create_pipe("sentencizer")
    spacy_nlp.add_pipe(sentencizer)


    if args.extraction_type == PATHIE_EXTRACTION:
        amount_files, doc2tags = filter_and_write_documents_to_tempdir(len(ids_to_process), args.input,
                                                                                 ie_input_dir, ie_filelist_file, spacy_nlp)
        time_filtered = datetime.now()
        corenlp_output_dir = os.path.join(working_dir, 'corenlp_output')
        if not os.path.exists(corenlp_output_dir):
            os.mkdir(corenlp_output_dir)
        pathie_run_corenlp(core_nlp_dir, corenlp_output_dir, ie_filelist_file)
        logging.info("Processing output ...", end="")
        start = datetime.now()
        # Process output
        pathie_process_corenlp_output(corenlp_output_dir, amount_files, args.output, doc2tags)
        logging.info((" done in {}".format(datetime.now() - start)))
    else:
        # now filter these documents
        amount_ie_docs = filter_and_write_documents_to_tempdir(len(ids_to_process), args.input,
                                                                                 ie_input_dir, ie_filelist_file, spacy_nlp)
        time_filtered = datetime.now()
        if amount_ie_docs == 0:
            logging.info('No files to process for IE - stopping')
        else:
            run_openie(core_nlp_dir, ie_output_file, ie_filelist_file)
            logging.info("Processing output ...")
            start = datetime.now()
            # Process output
            process_output(ie_output_file, args.output)
            logging.info("Done in {}".format(datetime.now() - start))

    time_open_ie = datetime.now()
    # add document as processed to database
    mark_document_as_processed_by_ie(ids_to_process, args.collection, args.extraction_type)
    logging.info('Process finished in {}s ({}s export, {}s filtering and {}s ie)'
                 .format(time_open_ie-time_start, time_exported-time_start, time_filtered-time_exported,
                         time_open_ie-time_filtered))

    logging.info('Removing temp directory...')
    shutil.rmtree(working_dir)
    logging.info('Finished')


if __name__ == "__main__":
    main()
