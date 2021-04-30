import glob
import logging
import os
from argparse import ArgumentParser
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from narrant.backend import models
from narrant.backend.database import Session
from narrant.backend.models import Document, DocumentTranslation
from narraint.progress import print_progress_with_eta
from narraint.pubtator.translation.cord19.filereader import FileReader
from narraint.pubtator.translation.cord19.metareader import MetaReader
from narraint.pubtator.translation.md5_hasher import get_md5_hash, get_md5_hash_str

UNIQUE_ID_START = 100000
NEXT_DOCUMENT_ID_OFFSET = 100000
PARAGRAPH_TITLE_DUMMY = "Section"


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
        self.meta_file = metadata_file
        self.meta = MetaReader(metadata_file)
        logging.debug(f"{len(self.meta)} entries found.")
        self.collection = collection
        self.input_dir = input_dir
        self.output_file = output_file
        self.excluded_hashs = self.collect_excluded_hashs(crosscollections)
        self.id_offset = get_offset()
        self.timestamp = datetime.now()
        logging.debug(f"starting at id {self.id_offset}")

    def collect_excluded_hashs(self, exclude_collections=None):
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


    def translate(self):
        """
           recursively searches for all .json files in input_dir, sanitizes them and converts them to a pubtator format.
           :parm input_dir: directory containing the json files
           :param output_dir: an (existing) file path to write the pubtator output to
        """
        print('searching all json files in {}'.format(self.input_dir))
        all_json = glob.glob(f'{self.input_dir}/**/*.json', recursive=True)
        print('{} json files found'.format(len(all_json)))
        start_time = datetime.now()
        current_id = 0
        logging.info("Translating...")
        cord_uids_without_fulltexts = set(self.meta.cord_uid_index.keys())
        already_translated = []
        tanslated_jsons = []

        with open(self.output_file, 'w') as f:
            for json_file in all_json:
                try:
                    file = FileReader(json_file)
                    md5_hash = get_md5_hash(json_file)
                    metadata = self.meta.get_metadata_by_id(file.paper_id)
                    cord_uids_without_fulltexts.discard("".join(metadata['cord_uid']))

                    if md5_hash in self.excluded_hashs: #Document already translated
                        already_translated.append(md5_hash)
                        print_progress_with_eta('converting', current_id + len(already_translated), len(self.meta),
                                                start_time)
                        #logging.debug(f"skipping {file.paper_id}: already translated")
                        continue
                    doc_id = self.id_offset + (NEXT_DOCUMENT_ID_OFFSET * current_id)
                    self.insert_translation(doc_id, md5_hash, metadata, os.path.basename(json_file))
                    tanslated_jsons.append(md5_hash)
                    # export title + abstract

                    if len(file.abstract) > 0:
                        content = Document.create_pubtator(doc_id, file.title, file.abstract)
                        f.write(content + '\n')

                    elif len(metadata['abstract']) > 0:
                        content = Document.create_pubtator(doc_id, file.title, " ".join(metadata['abstract']))
                        f.write(content + '\n')

                    for body_text_id, body_text in enumerate(file.body_texts):
                        if body_text_id >= NEXT_DOCUMENT_ID_OFFSET:
                            raise ValueError('Overflow body id - increase id range for document bodies')
                        artificial_doc_id = doc_id + body_text_id + 1
                        content = Document.create_pubtator(artificial_doc_id, PARAGRAPH_TITLE_DUMMY, body_text)
                        f.write(content + '\n')

                    current_id += 1
                    print_progress_with_eta('converting', current_id + len(already_translated), len(self.meta),
                                            start_time)
                except KeyError:
                    print('skip: {}'.format(json_file))
            abstracts_from_meta = []
            for cord_uid in cord_uids_without_fulltexts:
                was_new, md5_hash = self.translate_from_meta(cord_uid, current_id, f)
                if was_new:
                    current_id += 1
                    abstracts_from_meta.append(md5_hash)
                else:
                    already_translated.append(md5_hash)
                print_progress_with_eta('converting', current_id + len(already_translated), len(self.meta),
                                        start_time)

        logging.info(f"Done. {len(tanslated_jsons) + len(abstracts_from_meta)} docs inserted,"  
                     f" {len(already_translated)} docs already in database.")
        logging.info(f"{len(abstracts_from_meta)} docs constructed from abstracts in metadata file.")

    def translate_from_meta(self, cord_uid, current_id, f):
        metadata = self.meta.get_metadata_by_cord_uid(cord_uid)
        title, abstract, md5_hash = self.meta.get_doc_content(cord_uid, generate_md5=True)
        doc_id = self.id_offset + (current_id * NEXT_DOCUMENT_ID_OFFSET)
        content = Document.create_pubtator(doc_id, title, abstract)
        if md5_hash not in self.excluded_hashs:
            f.write(content + "\n")
            self.insert_translation(doc_id, md5_hash, metadata, os.path.basename(self.meta_file))
            return True, md5_hash
        else:
            return False, md5_hash

    def insert_translation(self, art_id, md5_hash, metadata, source=None):
        session = Session.get()
        insert_query = insert(models.DocumentTranslation).values(
            document_id=art_id,
            document_collection=self.collection,
            source_doc_id=metadata['cord_uid'][0],
            md5=md5_hash,
            date_inserted=self.timestamp,
            source=source
        )
        session.execute(insert_query)
        session.commit()


def get_offset():
    session = Session.get()
    max_id = session.query(func.max(DocumentTranslation.document_id)).scalar()
    max_id = max_id if max_id else 0
    return max_id - max_id % NEXT_DOCUMENT_ID_OFFSET + NEXT_DOCUMENT_ID_OFFSET


if __name__ == "__main__":
    main()
