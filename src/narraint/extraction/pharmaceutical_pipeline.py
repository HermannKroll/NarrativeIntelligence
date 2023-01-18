import argparse
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from typing import Set

from spacy.lang.en import English

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.cleaning.relation_vocabulary import RelationVocabulary
from kgextractiontoolbox.config import NLP_CONFIG
from kgextractiontoolbox.document.count import count_documents
from kgextractiontoolbox.document.export import export
from kgextractiontoolbox.extraction.extraction_utils import filter_and_write_documents_to_tempdir
from kgextractiontoolbox.extraction.loading.load_extractions import clean_and_load_predications_into_db
from kgextractiontoolbox.extraction.loading.load_pathie_extractions import read_pathie_extractions_tsv
from kgextractiontoolbox.extraction.pathie.main import pathie_run_corenlp, pathie_process_corenlp_output_parallelized
from kgextractiontoolbox.extraction.pathie_stanza.main import run_stanza_pathie
from kgextractiontoolbox.extraction.pipeline import mark_document_as_processed_by_ie, retrieve_document_ids_to_process
from kgextractiontoolbox.extraction.versions import PATHIE_EXTRACTION, OPENIE_EXTRACTION, PATHIE_STANZA_EXTRACTION, \
    OPENIE6_EXTRACTION, OPENIE51_EXTRACTION
from kgextractiontoolbox.util.helpers import chunks
from narraint.backend.database import SessionExtended
from narraint.backend.models import Document
from narraint.extraction.loading.clean_load_genes import clean_and_translate_gene_ids

DOCUMENTS_TO_PROCESS_IN_ONE_BATCH = 500000


def process_documents_ids_in_pipeline(ids_to_process: Set[int], document_collection, extraction_type, workers=1,
                                      corenlp_config=NLP_CONFIG,
                                      relation_vocab: RelationVocabulary = None,
                                      consider_sections=False):
    """
    Performs fact extraction for the given documents with the selected extraction type
    The document texts and tags will be exported automatically
    The extracted facts will be inserted into the predication table
    Stores the processed document ids in the ProcessedbyIE table
    :param ids_to_process: a set of document ids to process
    :param document_collection: the corresponding document collection
    :param extraction_type: the extraction type (e.g. PathIE)
    :param workers: the number of parallel workers (if extraction method is parallelized)
    :param corenlp_config: the nlp config
    :param relation_vocab: the relation vocabulary for PathIE (optional)
    :param consider_sections: Should document sections be considered for text generation?

    :return: None
    """
    # Read config
    with open(corenlp_config) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]

    time_start = datetime.now()
    working_dir = tempfile.mkdtemp()
    document_export_file = os.path.join(working_dir, 'document_export.json')
    ie_input_dir = os.path.join(working_dir, 'ie')
    ie_filelist_file = os.path.join(working_dir, 'ie_filelist.txt')
    ie_output_file = os.path.join(working_dir, 'ie.output')
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)
    if not os.path.exists(ie_input_dir):
        os.mkdir(ie_input_dir)

    logging.info('Process will work in: {}'.format(working_dir))
    # export them with their tags
    logging.info(f'Exporting documents to: {document_export_file}')
    export(document_export_file, export_tags=True, document_ids=ids_to_process, collection=document_collection,
           content=True, export_sections=consider_sections, export_format="json")

    time_exported = datetime.now()

    logging.info('Counting documents...')
    count_ie_files = count_documents(document_export_file)
    time_filtered = datetime.now()
    time_load = datetime.now()
    if count_ie_files == 0:
        logging.info('No files to process for IE - stopping')
    else:
        if extraction_type == PATHIE_EXTRACTION:
            logging.info('Init spacy nlp...')
            spacy_nlp = English()  # just the language with no model
            spacy_nlp.add_pipe("sentencizer")

            logging.info('Filtering documents...')
            count_ie_files, doc2tags = filter_and_write_documents_to_tempdir(len(ids_to_process), document_export_file,
                                                                             ie_input_dir, ie_filelist_file, spacy_nlp,
                                                                             workers,
                                                                             consider_sections=consider_sections)

            corenlp_output_dir = os.path.join(working_dir, 'corenlp_output')
            if not os.path.exists(corenlp_output_dir):
                os.mkdir(corenlp_output_dir)

            pathie_run_corenlp(core_nlp_dir, corenlp_output_dir, ie_filelist_file, worker_no=workers)

            logging.info("Processing output ...")
            start = datetime.now()

            pred_vocab = relation_vocab.relation_dict if relation_vocab else None
            # Process output
            pathie_process_corenlp_output_parallelized(corenlp_output_dir, count_ie_files, ie_output_file, doc2tags,
                                                       workers=workers, predicate_vocabulary=pred_vocab)
            logging.info((" done in {}".format(datetime.now() - start)))
        elif extraction_type == PATHIE_STANZA_EXTRACTION:
            pred_vocab = relation_vocab.relation_dict if relation_vocab else None
            logging.info('Starting PathIE Stanza...')
            start = datetime.now()
            run_stanza_pathie(document_export_file, ie_output_file, predicate_vocabulary=pred_vocab,
                              consider_sections=consider_sections)
            logging.info((" done in {}".format(datetime.now() - start)))

        logging.info('Loading extractions into database...')
        time_load = datetime.now()
        logging.info(f'Reading extraction from {ie_output_file}...')
        predications = read_pathie_extractions_tsv(ie_output_file, load_symmetric=False)
        logging.info('{} extractions read'.format(len(predications)))
        logging.info('Cleaning gene ids...')
        predications_cleaned = clean_and_translate_gene_ids(predications)
        logging.info('Inserting {} predications'.format(len(predications_cleaned)))
        clean_and_load_predications_into_db(predications_cleaned, document_collection, extraction_type)
        logging.info('finished')

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
    parser.add_argument("-i", "--idfile", help="Document ID file (documents must be in database)")
    parser.add_argument("-et", "--extraction_type", required=True, help="the extraction method",
                        choices=list(
                            [OPENIE_EXTRACTION, OPENIE51_EXTRACTION, OPENIE6_EXTRACTION, PATHIE_EXTRACTION,
                             PATHIE_STANZA_EXTRACTION]))
    parser.add_argument("-c", "--collection", required=True, help="Name of the given document collection")
    parser.add_argument("--config", help="OpenIE / PathIE Configuration file", default=NLP_CONFIG)
    parser.add_argument("-w", "--workers", help="number of parallel workers", default=1, type=int)
    parser.add_argument("-bs", "--batch_size",
                        help="Batch size (how many documents should be processed and loaded in a batch)",
                        default=DOCUMENTS_TO_PROCESS_IN_ONE_BATCH, type=int)
    parser.add_argument('--relation_vocab', default=None, help='Path to a relation vocabulary (json file)')
    parser.add_argument("--sections", action="store_true", default=False,
                        help="Should the section texts be considered in the extraction step?")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    if args.relation_vocab:
        relation_vocab = RelationVocabulary()
        relation_vocab.load_from_json(args.relation_vocab)
    else:
        relation_vocab = None
    document_ids = set()
    if args.idfile:
        logging.info('Reading id file: {}'.format(args.idfile))
        with open(args.idfile, 'r') as f:
            document_ids = set([int(line.strip()) for line in f])
        logging.info(f'{len(document_ids)} documents in id file')
    else:
        logging.info(f'No id file given - query all known ids for document collection: {args.collection}')
        session = SessionExtended.get()
        for r in session.query(Document.id).filter(Document.collection == args.collection).distinct():
            document_ids.add(r[0])
        logging.info(f'{len(document_ids)} were found in db')
    document_ids_to_process = retrieve_document_ids_to_process(args.collection, args.extraction_type,
                                                               document_id_filter=document_ids)
    num_of_chunks = int(len(document_ids_to_process) / args.batch_size) + 1
    logging.info(f'Splitting task into {num_of_chunks} chunks...')
    for idx, batch_ids in enumerate(chunks(list(document_ids_to_process), args.batch_size)):
        logging.info('=' * 60)
        logging.info(f'       Processing chunk {idx}/{num_of_chunks}...')
        logging.info('=' * 60)
        logging.info(f'{len(batch_ids)} ids have to been processed in this batch')
        process_documents_ids_in_pipeline(batch_ids, args.collection, args.extraction_type, corenlp_config=args.config,
                                          workers=args.workers, relation_vocab=relation_vocab,
                                          consider_sections=args.sections)


if __name__ == "__main__":
    main()
