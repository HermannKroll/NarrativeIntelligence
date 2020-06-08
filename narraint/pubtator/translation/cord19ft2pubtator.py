import glob
import json
import hashlib
import logging
from argparse import ArgumentParser
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm.query import Query

from narraint.backend import models
from narraint.backend.database import Session
from narraint.backend.models import Document, DocumentTranslation
from narraint.progress import print_progress_with_eta
from narraint.pubtator.translation.metareader import MetaReader

UNIQUE_ID_START = 100000
NEXT_DOCUMENT_ID_OFFSET = 100000


class FileReader:
    def __init__(self, file_path):
        with open(file_path) as file:
            content = json.load(file)
            self.paper_id = content['paper_id']
            self.title = ""
            self.abstract = []
            self.body_texts = []
            # Title
            self.title = content['metadata']["title"]
            # Abstract
            if 'abstract' in content:
                for entry in content['abstract']:
                    self.abstract.append(entry['text'])
            # Body text
            for entry in content['body_text']:
                self.body_texts.append(entry['text'])
            self.abstract = '\n'.join(self.abstract)

    def __repr__(self):
        return f'{self.paper_id}: {self.abstract[:200]}... {self.body_text[:200]}...'


def main():
    parser = ArgumentParser(description="Collect and convert PMC files from a list of pmc-ids")
    parser.add_argument("collection", help="Collection to crosscheck for already scanned documents "
                                           "and insert new metadata")
    parser.add_argument("input", help="Root Directory of Cord19m2 data set")
    parser.add_argument("metadata", help="Path to metadata.csv file")
    parser.add_argument("output", help="Output of the resulting Pubtator file")
    parser.add_argument("--crosscollections", "-c", nargs='+', help="Collections to crosscheck")
    parser.add_argument("--loglevel", "-l", help="Loglevel", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel.upper())
    translator = Translator(args.collection, args.input, args.output, args.metadata, args.crosscollections)
    translator.translate()

class Translator:
    def __init__(self, collection, input_dir, output_file, metadata_file, crosscollections):
        logging.debug("Reading metadata...")
        self.meta = MetaReader(metadata_file)
        logging.debug(f"{len(self.meta)} entries found.")
        self.collection = collection
        self.input_dir = input_dir
        self.output_file = output_file
        self.excluded_shas = self.collect_excluded_shas(crosscollections)
        self.id_offset = get_offset()
        self.timestamp = datetime.now()
        logging.debug(f"starting at id {self.id_offset}")

    def collect_excluded_shas(self, exclude_collections=None):
        if exclude_collections is None:
            exclude_collections = []
        exclude_collections = {c for c in exclude_collections}
        exclude_collections.add(self.collection)
        session = Session.get()
        query = session.query(DocumentTranslation).filter(
            DocumentTranslation.document_collection.in_(exclude_collections)).with_entities(
            DocumentTranslation.md5
        )
        return [row.md5 for row in query]


    """
    recursively searches for all .json files in input_dir, sanitizes them and converts them to a pubtator format. 
    :parm input_dir: directory containing the json files
    :param output_dir: an (existing) file path to write the pubtator output to
    """
    def translate(self):
        print('searching all json files in {}'.format(self.input_dir))
        all_json = glob.glob(f'{self.input_dir}/**/*.json', recursive=True)
        print('{} json files found'.format(len(all_json)))
        start_time = datetime.now()
        current_id = 0
        logging.info("Translating...")
        cord_uids_without_fulltexts = set(self.meta.cord_uid_index.keys())

        with open(self.output_file, 'w') as f:
            for json_file in all_json:
                try:
                    file = FileReader(json_file)
                    md5_hash = get_md5_hash(file)
                    metadata = self.meta.get_metadata_by_id(file.paper_id)
                    cord_uids_without_fulltexts.remove(metadata['cord_uid'])

                    if md5_hash in self.excluded_shas: #Document already translated
                        logging.debug(f"skipping {file.paper_id}: already translated")
                        continue
                    doc_id = self.id_offset + (NEXT_DOCUMENT_ID_OFFSET * current_id)
                    # export title + abstract
                    if len(file.abstract) > 0:
                        content = Document.create_pubtator(doc_id, file.title, file.abstract)
                        f.write(content + '\n')
                        self.insert_translation(doc_id, md5_hash, metadata)
                    elif len(metadata['abstract']) > 0:
                        content = Document.create_pubtator(doc_id, file.title, " ".join(metadata['abstract']))
                        f.write(content + '\n')
                        self.insert_translation(doc_id, md5_hash, metadata)

                    for body_text_id, body_text in enumerate(file.body_texts):
                        if body_text_id >= NEXT_DOCUMENT_ID_OFFSET:
                            raise ValueError('Overflow body id - increase id range for document bodies')
                        artificial_doc_id = doc_id + body_text_id + 1
                        content = Document.create_pubtator(artificial_doc_id, "Section", body_text)
                        f.write(content + '\n')
                        self.insert_translation(artificial_doc_id, md5_hash, metadata)

                    current_id += 1
                    print_progress_with_eta('converting', current_id, len(all_json), start_time)
                except KeyError:
                    print('skip: {}'.format(json_file))
            for cord_uid in cord_uids_without_fulltexts:
                metadata = self.meta.cord_uid_index[cord_uid]
                doc_id = current_id * NEXT_DOCUMENT_ID_OFFSET
                title = ";".join(metadata['title'])
                abstract = ";".join(metadata['abstract'])
                content = Document.create_pubtator(doc_id, title, abstract)
                md5_hash = get_md5_hash_str(content)
                if md5_hash not in self.excluded_shas:
                    f.write(content + "\n")
                    self.insert_translation(doc_id, md5_hash, metadata)
                current_id += 1

    def insert_translation(self, art_id, md5_hash, metadata):
        session = Session.get()
        insert_query = insert(models.DocumentTranslation).values(
            document_id=art_id,
            document_collection=self.collection,
            source_doc_id=metadata['cord_uid'][0],
            md5=md5_hash,
            date_inserted=self.timestamp
        )
        session.execute(insert_query)
        session.commit()


def get_offset():
    session = Session.get()
    max_id = session.query(func.max(DocumentTranslation.document_id)).scalar()
    max_id = max_id if max_id else 0
    return max_id - max_id % NEXT_DOCUMENT_ID_OFFSET + NEXT_DOCUMENT_ID_OFFSET


def get_md5_hash(file):
    m = hashlib.md5()
    if file:
        with open(file) as f:
            m.update(str.encode(f.read()))
            return m.hexdigest()


def get_md5_hash_str(str_input):
    m = hashlib.md5()
    m.update(str_input)
    return m.hexdigest()


if __name__ == "__main__":
    main()
