import argparse
import json
import os
import tempfile
from datetime import datetime
import logging
import shutil
from spacy.lang.en import English

from narraint.cleaning.predicate_vocabulary import create_predicate_vocab
from narrant.preprocessing import enttypes
from narraint.backend.database import SessionExtended
from narrant.backend.export import export
from narraint.backend.models import DocProcessedByIE, Document
from narraint.extraction.extraction_utils import filter_and_write_documents_to_tempdir
from narraint.extraction.pathie.load_extractions import load_pathie_extractions
from narraint.extraction.pathie.main import pathie_run_corenlp, pathie_process_corenlp_output_parallelized
from narraint.extraction.versions import PATHIE_EXTRACTION, OPENIE_EXTRACTION, PATHIE_STANZA_EXTRACTION
from narraint.config import NLP_CONFIG
from narrant.util.helpers import chunks

DOCUMENTS_TO_PROCESS_IN_ONE_BATCH = 500000


def retrieve_document_ids_to_process(document_ids: [int], document_collection: str, extraction_type: str):
    """
    Computes the set of document that have not been processed yet
    Utilizes the ProcessedByIE table
    :param document_ids: the set of document ids
    :param document_collection: the corresponding document collection
    :param extraction_type: the extraction type
    :return: a set of document ids that have not been processed yet
    """
    logging.info('{} ids retrieved from id file..'.format(len(document_ids)))
    session = SessionExtended.get()
    logging.info('Retrieving document ids from document table...')
    doc_ids_in_db = set()
    q = session.query(Document.id).filter(Document.collection == document_collection)
    for r in session.execute(q):
        doc_ids_in_db.add(r[0])

    logging.info('{} document ids in Document table'.format(len(doc_ids_in_db)))
    logging.info('Retrieving already processed document ids from database...')
    q = session.query(DocProcessedByIE.document_id) \
        .filter_by(document_collection=document_collection) \
        .filter_by(extraction_type=extraction_type)
    processed_ids = set()
    for r in session.execute(q):
        processed_ids.add(r[0])
    logging.info('{} document ids are in the database'.format(len(processed_ids)))
    missing_ids = document_ids.intersection(doc_ids_in_db)
    missing_ids = missing_ids.difference(processed_ids)
    logging.info('{} ids have already been processed and will be skipped'.format(len(document_ids) - len(missing_ids)))
    logging.info('{} remaining document ids to process...'.format(len(missing_ids)))
    return missing_ids


def mark_document_as_processed_by_ie(document_ids: [int], document_collection: str, extraction_type: str):
    """
    Insert a set of document ids into the ProcessedByIE table
    :param document_ids: a set of document ids
    :param document_collection: the corresponding document collection
    :param extraction_type: the extraction type
    :return: None
    """
    logging.info('Inserting processed document ids into database...')
    doc_inserts = []
    for doc_id in document_ids:
        doc_inserts.append(dict(document_id=doc_id,
                                document_collection=document_collection,
                                extraction_type=extraction_type))
    session = SessionExtended.get()
    session.bulk_insert_mappings(DocProcessedByIE, doc_inserts)
    session.commit()
    logging.info(f'{len(doc_inserts)} document ids have been inserted')


def process_documents_ids_in_pipeline(document_ids: [int], document_collection, extraction_type, workers=1,
                                      corenlp_config=NLP_CONFIG, check_document_ids=True):
    """
    Performs fact extraction for the given documents with the selected extraction type
    The document texts and tags will be exported automatically
    The extracted facts will be inserted into the predication table
    Stores the processed document ids in the ProcessedbyIE table
    :param document_ids: a set of document ids to process
    :param document_collection: the corresponding document collection
    :param extraction_type: the extraction type (e.g. PathIE)
    :param workers: the number of parallel workers (if extraction method is parallelized)
    :param corenlp_config: the nlp config
    :param check_document_ids: should the the document ids be checked against db
    :return: None
    """
    # Read config
    with open(corenlp_config) as f:
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
    if check_document_ids:
        ids_to_process = retrieve_document_ids_to_process(document_ids, document_collection, extraction_type)
    else:
        ids_to_process = document_ids
    # export them with their tags
    export(document_export_file, enttypes.ALL, document_ids=ids_to_process, collection=document_collection,
           content=True)
    time_exported = datetime.now()
    logging.info('Init spacy nlp...')
    spacy_nlp = English()  # just the language with no model
    sentencizer = spacy_nlp.create_pipe("sentencizer")
    spacy_nlp.add_pipe(sentencizer)

    logging.info('Filtering documents...')
    amount_ie_docs, doc2tags = filter_and_write_documents_to_tempdir(len(ids_to_process), document_export_file,
                                                                     ie_input_dir, ie_filelist_file, spacy_nlp,
                                                                     workers)
    time_filtered = datetime.now()
    time_load = datetime.now()
    if amount_ie_docs == 0:
        logging.info('No files to process for IE - stopping')
    else:
        if extraction_type == PATHIE_EXTRACTION:
            corenlp_output_dir = os.path.join(working_dir, 'corenlp_output')
            if not os.path.exists(corenlp_output_dir):
                os.mkdir(corenlp_output_dir)

            pathie_run_corenlp(core_nlp_dir, corenlp_output_dir, ie_filelist_file)

            logging.info("Processing output ...")
            start = datetime.now()
            # Process output
            pathie_process_corenlp_output_parallelized(corenlp_output_dir, amount_ie_docs, ie_output_file, doc2tags,
                                                       workers=workers, predicate_vocabulary=create_predicate_vocab())
            logging.info((" done in {}".format(datetime.now() - start)))

            logging.info('Loading extractions into database...')
            time_load = datetime.now()
            load_pathie_extractions(ie_output_file, document_collection, extraction_type)
        elif extraction_type == PATHIE_STANZA_EXTRACTION:
            # Todo: Implement
            raise NotImplementedError
        elif extraction_type == OPENIE_EXTRACTION:
            # Todo: Implement
            raise NotImplementedError
    time_open_ie = datetime.now()
    # add document as processed to database
    mark_document_as_processed_by_ie(ids_to_process, document_collection, extraction_type)
    logging.info('Process finished in {}s ({}s export, {}s filtering, {}s ie and {}s load)'
                 .format(time_open_ie - time_start, time_exported - time_start, time_filtered - time_exported,
                         time_open_ie - time_filtered, time_open_ie - time_load))

    logging.info('Removing temp directory...')
    shutil.rmtree(working_dir)
    logging.info('Finished')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idfile", help="Document ID file (documents must be in database)")
    parser.add_argument("-et", "--extraction_type", required=True, help="OpenIE|PathIE|PathIEStanza")
    parser.add_argument("-c", "--collection", required=True, help="Name of the given document collection")
    parser.add_argument("--config", help="OpenIE / PathIE Configuration file", default=NLP_CONFIG)
    parser.add_argument("-w", "--workers", help="number of parallel workers", default=1, type=int)
    parser.add_argument("-bs", "--batch_size",
                        help="Batch size (how many documents should be processed and loaded in a batch)",
                        default=DOCUMENTS_TO_PROCESS_IN_ONE_BATCH, type=int)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    if args.extraction_type not in [PATHIE_EXTRACTION, PATHIE_STANZA_EXTRACTION, OPENIE_EXTRACTION]:
        error_msg = 'extraction type must either be {}, {} or {}'.format(PATHIE_EXTRACTION, PATHIE_STANZA_EXTRACTION,
                                                                         OPENIE_EXTRACTION)
        raise argparse.ArgumentError(None, message=error_msg)

    logging.info('Reading id file: {}'.format(args.idfile))
    with open(args.idfile, 'r') as f:
        document_ids = set([int(line.strip()) for line in f])

    logging.info(f'{len(document_ids)} documents in id file')
    document_ids_to_process = retrieve_document_ids_to_process(document_ids, args.collection, args.extraction_type)
    num_of_chunks = int(len(document_ids_to_process) / args.batch_size)
    logging.info(f'Splitting task into {num_of_chunks} chunks...')
    for idx, batch_ids in enumerate(chunks(list(document_ids_to_process), args.batch_size)):
        logging.info('=' * 60)
        logging.info(f'       Processing chunk {idx}/{num_of_chunks}...')
        logging.info('=' * 60)
        process_documents_ids_in_pipeline(batch_ids, args.collection, args.extraction_type, corenlp_config=args.config,
                                          check_document_ids=False, workers=args.workers) # have been checked before


if __name__ == "__main__":
    main()
