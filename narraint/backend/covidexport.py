import argparse
import logging
import csv
import os
import unicodedata
from datetime import datetime
from glob import glob

import json

from sqlalchemy import func

from narraint.backend.database import Session
from narraint.backend.models import DocumentTranslation, Tag
from narraint.backend.export import create_tag_query, TAG_BUFFER_SIZE
from narraint.entity import enttypes
from narraint.entity.enttypes import TAG_TYPE_MAPPING
from narraint.pubtator.regex import ILLEGAL_CHAR
from narraint.progress import print_progress_with_eta
from narraint.pubtator.translation.cord19.cord19ft2pubtator import NEXT_DOCUMENT_ID_OFFSET, PARAGRAPH_TITLE_DUMMY
from narraint.pubtator.translation.cord19.filereader import FileReader
from narraint.pubtator.translation.cord19.metareader import MetaReader
import narraint.pubtator.translation.md5_hasher

TITLE = "title"
ABSTRACT = "abstract"
BODY = "body"

MAX_SCAN_WIDTH = 1000


class CovExport:
    """
    This class encapsulates the proce
    """

    def __init__(self, out_fn, tag_types, json_root, meta_file, collection=None, document_ids=None, logger=logging):
        self.logger = logger
        self.out_file = out_fn
        logger.info("Setting up...")
        logger.debug("Collecting JSONs...")
        self.file_dict = _build_file_dict(json_root)
        logger.debug(f"Found {len(self.file_dict)} jsons")
        self.tag_types = tag_types
        logger.debug("Reading Metadata file...")
        self.meta = MetaReader(meta_file)
        logger.debug(f"{len(self.meta)} entries in Metadata file")
        logger.debug("Sending Query to document_translation...")
        self.collection = collection
        self.document_ids = document_ids
        self.translation_query = query_document_translation(collection, document_ids)
        logger.debug("Building index...")
        self._docid_index = self._build_docid_index()
        logger.debug(f"{len(self._docid_index)} rows for collection {collection if collection else 'any'} and "
                     f"{len(document_ids) if document_ids else 'any'}ids")
        self.tag_buffer = TAG_BUFFER_SIZE

    def _build_docid_index(self):
        return {row.document_id: n for n, row in enumerate(self.translation_query)}

    def get_translation_by_docid(self, docid):
        return self.translation_query[self._docid_index[docid]]

    def get_meta_by_artid(self, artid):
        return self.meta.get_metadata_by_cord_uid(self.get_translation_by_docid(artid).source_doc_id)

    def get_get_sourcefile_by_docid(self, docid):
        translation = self.get_translation_by_docid(docid)
        return self.file_dict[translation.source] if translation.source in self.file_dict else None

    def get_content_from_meta(self, document_id, check_md5=True):
        translation = self.get_translation_by_docid(document_id)
        if '.csv' in translation.source:
            title, abstract, md5 = self.meta.get_doc_content(translation.source_doc_id, generate_md5=check_md5)
        else:
            file = self.file_dict[translation.source]

    def create_document_json(self, document_id):
        """
        :param document_id:
        :return: output document id, meta dict if found, else {}
        """
        translation = self.get_translation_by_docid(document_id)
        metadata = self.get_meta_by_artid(document_id)
        output_document_id = os.path.basename(translation.source)
        if metadata:
            if "metadata.csv" in translation.source:
                output_document_id += "/" + translation.source_doc_id
            cord_uid = metadata['cord_uid'][0]
            source_collection = metadata['source_x']
            output_dict = {"cord_uid": cord_uid, "source_collection": source_collection}
            return output_document_id, output_dict
        else:
            return output_document_id, {}

    @staticmethod
    def find_tags_in_tit_abs(tag_list, abstract, par_id, title=PARAGRAPH_TITLE_DUMMY):
        tags_found = 0
        text = "_" + title + "__" + abstract
        logging.debug(f"{par_id}: >{text}<")
        san_index = create_sanitized_index(text)
        output_json = []
        for tag in tag_list:
            found = False
            try:
                san_start = san_index[tag.start]
                length = san_index[tag.end] - san_start
                json_par_id = par_id
                if par_id == 0:
                    if san_start < len(title) + 1:  # tag in title
                        san_start -= 1
                        json_par_id = 0
                    else:
                        san_start -= 3
                        json_par_id = 1
                else:
                    san_start -= len("_" + title + "__")
                    json_par_id = par_id + 1
                san_end = san_start + length
                # if json_par_id == 0:
                #     logging.debug(f"TIT: {text[0:san_start + 1]}"
                #                   f"|{text[san_start + 1:san_end + 1]}|"
                #                   f"{text[san_end + 1: len(title)]} @@@ {tag.ent_str}, {tag.start} -> {san_start}")
                # elif json_par_id == 1:
                #     logging.debug(f"ABS: {text[san_start-50:san_start + 3]}"
                #                   f"|{text[san_start + 3:san_end + 3]}|"
                #                   f"{text[san_end + 3: san_end + 51]} @@@ {tag.ent_str}, {tag.start} -> {san_start}")
                # else:
                #     logging.debug(f"FUL: {text[san_start-50:san_start+3+len(title)]}"
                #           f"|{text[san_start+3+len(title):san_end+3+len(title)]}|"
                #           f"{text[san_end+3+len(title):san_end+51]} @@@ {tag.ent_str}, {tag.start} -> {san_start}")

                output_json.append({
                    "location": {
                        "paragraph": json_par_id,
                        "start": san_start,
                        "end": san_end
                    },
                    "entity_str": tag.ent_str,
                    "entity_type": tag.ent_type,
                    "entity_id": tag.ent_id,
                })
            except:
                logging.debug(f"{tag}not found")

        return output_json

    def create_tag_json(self, tag_types):
        """
        This abomination hopefully creates a json containing all the tags in the database.
        :param tag_types:
        :return: (tag_json, translation_json)
        """
        session = Session.get()
        tag_query = create_tag_query(session, self.collection, self.document_ids, tag_types, self.tag_buffer)
        tag_amount = session.query(func.count(Tag.document_id)).filter_by(document_collection=self.collection).scalar()
        logging.info(f"Retrieved {tag_amount} tags")
        tag_json = {}
        translation_json = {}

        start_time = datetime.now()
        last_translation = None
        last_art_id = None
        last_doc_id = None
        last_title = None
        last_abstract = None
        current_filereader = None
        last_out_doc_id = None
        source_hash = None
        database_hash = None
        document_valid = True

        tasklist = []
        task_total = 0
        found_total = 0
        for tag_no, tag in enumerate(tag_query):
            print_progress_with_eta("Reconstructing tag locations...", tag_no, tag_amount, start_time, 100000)
            par_id = tag.document_id % NEXT_DOCUMENT_ID_OFFSET
            doc_id = tag.document_id - par_id
            #if doc_id%100000000==0:
                #logging.info(f"At docid {doc_id}")

            if tag.document_id != last_art_id:  # new paragraph has begun
                try:
                    if tasklist:  # execute tasklist
                        last_par_id = last_art_id % NEXT_DOCUMENT_ID_OFFSET
                        tags = self.find_tags_in_tit_abs(tasklist, last_abstract, last_par_id,
                                                         last_title if last_par_id == 0 else PARAGRAPH_TITLE_DUMMY)
                        if last_out_doc_id in tag_json:
                            tag_json[last_out_doc_id].extend(tags)
                        else:
                            tag_json[last_out_doc_id] = tags
                        found_total += len(tags)
                        tasklist.clear()
                    last_art_id = tag.document_id
                    if doc_id != last_doc_id:  # New document: set FileReader if source is file
                        last_translation = self.get_translation_by_docid(doc_id)
                        if '.json' in last_translation.source:
                            sourcefile = self.get_get_sourcefile_by_docid(doc_id)
                            if not sourcefile:
                                logging.warning(f"Couldn't find sourcefile for doc_id {doc_id}")
                                current_filereader=None
                                continue
                            current_filereader = FileReader(sourcefile)
                            last_title = current_filereader.title
                        out_doc_id, doc_dict = self.create_document_json(doc_id)
                        last_out_doc_id = out_doc_id
                        translation_json[out_doc_id] = doc_dict
                        last_doc_id = doc_id
                    if '.csv' in last_translation.source:  # New paragraph + source is csv
                        title, abstract, md5 = self.meta.get_doc_content(last_translation.source_doc_id, True)
                        last_title, last_abstract = title, abstract
                        source_hash = md5
                    elif '.json' in last_translation.source:
                        abstract = current_filereader.get_paragraph(par_id)
                        if par_id == 0 and not abstract:  # abstract not included in JSON parse
                            _, abstract, _ = self.meta.get_doc_content(last_translation.source_doc_id)
                        last_abstract = abstract
                    document_valid=True
                except:
                    logging.warning(f"document {tag.document_id} is invalid, skipping")
                    document_valid=False
                    continue
            elif not document_valid:
                continue

            tasklist.append(tag)
            task_total += 1
        last_par_id = last_art_id % NEXT_DOCUMENT_ID_OFFSET
        tags = self.find_tags_in_tit_abs(tasklist, last_abstract, last_par_id,
                                         last_title if last_par_id == 0 else PARAGRAPH_TITLE_DUMMY)
        if last_out_doc_id in tag_json:
            tag_json[last_out_doc_id].extend(tags)
        else:
            tag_json[last_out_doc_id] = tags
        found_total += len(tags)
        tasklist.clear()
        logging.debug(f"total of tags added to tasklist:{task_total}")
        logging.debug(f"total of found tags: {found_total}")
        return tag_json, translation_json

    def export(self, tag_types, only_abstract=False):
        self.logger.info("Starting export...")
        tag_json, translation_json = self.create_tag_json(tag_types)

        logging.info(f"Writing fulltext tag json to {self.out_file}...")
        with open(self.out_file + "_entity_mentions_fulltexts.json", "w+") as f:
            json.dump(tag_json, f, indent=3)
        logging.info(f"Writing fulltext translation json to {self.out_file}.translation...")
        with open(self.out_file + "_translation.json", "w+") as f:
            json.dump(translation_json, f, indent=3)

        if only_abstract:
            # Gotta love your dict comprehensions :D
            abs_tag_json = {
                    key: [tag for tag in tag_json[key] if tag['location']['paragraph'] <= 1]
                    for key in tag_json.keys()
                    if [tag for tag in tag_json[key] if tag['location']['paragraph'] <= 1]
                }
            abs_translation_json = {key: translation_json[key] for key in abs_tag_json.keys()}
            logging.info(f"Writing abstract tag json to {self.out_file}.abstract ...")
            with open(self.out_file + "cord19v30_entity_mentions_title_and_abstract.json", "w+") as f:
                json.dump(abs_tag_json, f, indent=3)
            #logging.info(f"Writing abstract translation json to {self.out_file}.abstract.translation ...")
            #with open(self.out_file + ".abstract.translation", "w+") as f:
            #    json.dump(abs_translation_json, f, indent=3)


def _build_file_dict(json_root):
    files = glob(f"{json_root}/**/*", recursive=True)
    return {os.path.basename(f): f for f in files}


def query_document_translation(self, collection=None, document_ids=None):
    session = Session.get()
    translation_query = session.query(DocumentTranslation)
    if collection:
        translation_query = translation_query.filter(DocumentTranslation.document_collection == collection)
    if document_ids:
        translation_query = translation_query.filter(DocumentTranslation.document_id.in_(document_ids))
    return [row for row in translation_query]


def create_sanitized_index(content: str):
    """
    Takes a string and outputs a list to converts from sanitized index to non-sanitized index.
    :param content: The string to be indexed
    :return: List sanitized index -> non sanitized index
    """
    san_index = []
    for not_san_i, char in enumerate(content):
        unistr = unicodedata.normalize('NFD', char)
        unistr = ILLEGAL_CHAR.sub("", unistr)
        if unistr:
            san_index.append(not_san_i)
    return san_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("jsonroot")
    parser.add_argument("metafile")
    parser.add_argument("-a", "--only-abstract", action='store_true', help="additionally store json containing only"
                                                                           "tags in abstracts and titles")
    parser.add_argument("--ids", nargs="*", metavar="DOC_ID")
    parser.add_argument("--idfile", help='file containing document ids (one id per line)')
    parser.add_argument("-c", "--collection", help="Collection(s)", default=None)
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")
    parser.add_argument("-l", "--loglevel", default="INFO")
    args = parser.parse_args()

    ids = None
    if args.idfile:
        with open(args.idfile) as f:
            ids = [row for row in f]
    elif args.ids:
        ids = args.ids
    else:
        ids = None

    if args.tag:
        tag_types = enttypes.ALL if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]
    else:
        tag_types = None
    logging.basicConfig(level=args.loglevel.upper())
    exporter = CovExport(args.output, tag_types, args.jsonroot, args.metafile, args.collection, ids)
    exporter.export(tag_types, args.only_abstract)


def test_create_sanitzized_index():
    text = "Das ist ein schön€r Tag!"
    tag_start = 8
    tag_end = 18
    index = create_sanitized_index(text)
    san_start = index[tag_start]
    san_end = index[tag_end]
    print(f"{tag_start}:{tag_end} -> {san_start}:{san_end}")
    print(text)
    print(" "*tag_start + text[san_start:san_end])

#def test_abs_tag()
#    title



if __name__ == "__main__":
    main()
    #test_create_sanitzized_index()

