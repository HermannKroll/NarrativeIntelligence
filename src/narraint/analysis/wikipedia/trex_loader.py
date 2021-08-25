import argparse
import glob
import hashlib
import json
import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, Document, Sentence
from narrant.progress import print_progress_with_eta

TREX_DOCUMENT_COLLECTION = "trex"
SENTENCE_ID_START = 13259415


def _convert_wikidata_uri_to_id(uri):
    return uri.split('/')[-1]


def _get_processed_document_ids(session):
    q = session.query(Document.id).filter(Document.collection == TREX_DOCUMENT_COLLECTION)
    processed_ids = set()
    for r in q:
        processed_ids.add(int(r[0]))
    return processed_ids


def load_trex_dataset(input_dir):
    session = SessionExtended.get()
    all_json = glob.glob(f'{input_dir}/**/*.json', recursive=True)

    start_time = datetime.now()
    files_len = len(all_json)
    sentence_counter = 0
    logging.info('{} json files found'.format(files_len))
    logging.info('Query database for already processed document ids...')
    processed_document_ids = _get_processed_document_ids(session)
    logging.info('{} documents are already in the db (these will be skipped)'.format(len(processed_document_ids)))
    for idx, json_file in enumerate(all_json):
        print_progress_with_eta('loading trex in db', idx, files_len, start_time, print_every_k=1)
        with open(json_file) as file:
            docs_content = json.load(file)
            logging.info('Read {}'.format(json_file))
            document_values = []
            sentence_values = []
            predication_values = []
            for d_content in docs_content:
                document_id = int(_convert_wikidata_uri_to_id(d_content['docid'])[1:])
                if document_id in processed_document_ids:
                    continue
                processed_document_ids.add(document_id)
                title = d_content['title']
                text = d_content['text']

                document_values.append(dict(
                    id=document_id,
                    collection=TREX_DOCUMENT_COLLECTION,
                    title=title,
                    abstract=text
                ))

                sentidx2id = []
                for s_idx, sentence_boundaries in enumerate(d_content['sentences_boundaries']):
                    start = sentence_boundaries[0]
                    end = sentence_boundaries[1]
                    s_id = SENTENCE_ID_START + sentence_counter
                    sentence_counter += 1
                    s_txt = text[start:end]
                    sentidx2id.append(s_id)
                    sentence_values.append(dict(
                        id=s_id,
                        text=s_txt,
                        document_id=document_id,
                        document_collection=TREX_DOCUMENT_COLLECTION,
                        md5hash=hashlib.md5(s_txt.encode()).hexdigest()
                    ))

                existing_facts = set()
                for fact in d_content['triples']:
                    subject_ent = fact['subject']
                    subject_id = _convert_wikidata_uri_to_id(subject_ent['uri'])
                    subject_str = subject_ent['surfaceform']
                    predicate = fact['predicate']['surfaceform']
                    if not predicate:
                        predicate = ""  # db does enforce not null here
                    relation = _convert_wikidata_uri_to_id(fact['predicate']['uri'])
                    object_ent = fact['object']
                    object_id = _convert_wikidata_uri_to_id(object_ent['uri'])
                    object_str = object_ent['surfaceform']
                    confidence = fact['confidence']
                    extraction_type = fact['annotator']
                    sentence_id = sentidx2id[int(fact['sentence_id'])]

                    key = (document_id, subject_id, relation, object_id, sentence_id, extraction_type)
                    if key not in existing_facts:
                        existing_facts.add(key)
                        predication_values.append(dict(
                            document_id=document_id,
                            document_collection=TREX_DOCUMENT_COLLECTION,
                            subject_id=subject_id,
                            subject_str=subject_str,
                            subject_type="Entity",
                            predicate=predicate,
                            relation=relation,
                            object_id=object_id,
                            object_str=object_str,
                            object_type="Entity",
                            confidence=confidence,
                            sentence_id=sentence_id,
                            extraction_type=extraction_type
                        ))

                try:
                    session.bulk_insert_mappings(Document, document_values)
                    session.bulk_insert_mappings(Sentence, sentence_values)
                    session.bulk_insert_mappings(Predication, predication_values)
                    session.commit()
                    document_values.clear()
                    sentence_values.clear()
                    predication_values.clear()
                except IntegrityError:
                    logging.info('Skipping duplicated document: {}'.format(document_id))
                except ValueError:
                    logging.info('Cannot convert {} to an int'.format(d_content['docid']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Loading TREX directory...')
    load_trex_dataset(args.input_dir)
    logging.info('Finished')


if __name__ == "__main__":
    main()
