import argparse
import logging
import csv
import os
from datetime import datetime
from glob import glob

import json

from narraint.backend.database import Session
from narraint.backend.models import DocumentTranslation
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
        return self.file_dict[translation.source]

    def get_content_from_meta(self, document_id, check_md5=True):
        translation = self.get_translation_by_docid(document_id)
        if '.csv' in translation.source:
            title, abstract, md5 = self.meta.get_doc_content(translation.source_doc_id, generate_md5=check_md5)
        else:
            file = self.file_dict[translation.source]

    def create_document_json(self, document_id):
        translation = self.get_translation_by_docid(document_id)
        metadata = self.get_meta_by_artid(document_id)
        output_document_id = os.path.basename(translation.source).split('.')[0]
        cord_uid = metadata['cord_uid']
        source_collection = metadata['source_x']
        output_dict = {"cord_uid": cord_uid, "source_collection": source_collection}
        return output_document_id, output_dict

    @staticmethod
    def find_tags_in_tit_abs(tag_list, abstract, par_id, title=PARAGRAPH_TITLE_DUMMY):
        san_index = create_sanitized_index(" " + title + " " + abstract)
        output_json = []
        for tag in tag_list:
            san_start = san_index[tag.start-1]+1
            length = san_index[tag.end-1]-san_start+1
            json_par_id = par_id
            if san_start < len(title) + 1: # tag in title
                san_start -= 1
                json_par_id = 0
            else:
                san_start -= len(" " + title + " ")
                json_par_id = par_id + 1
            san_end = san_start + length
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
        return output_json

    def create_tag_json(self, tag_types):
        """
        This abomination hopefully creates a json containing all the tags in the database
        :param tag_types:
        :return:
        """
        session = Session.get()
        tag_query = create_tag_query(session, self.collection, self.document_ids, tag_types, self.tag_buffer)
        start_time = datetime.now()
        tag_json = {}

        last_translation = None
        last_art_id = None
        last_doc_id = None
        last_title = None
        last_abstract = None
        current_filereader = None
        last_out_doc_id = None
        source_hash = None
        database_hash = None

        tasklist = []
        for tag in tag_query:
            par_id = tag.document_id % NEXT_DOCUMENT_ID_OFFSET
            doc_id = tag.document_id - par_id

            if tag.document_id != last_art_id:  # new paragraph has begun
                if tasklist:  # execute tasklist
                    last_par_id = last_doc_id % NEXT_DOCUMENT_ID_OFFSET
                    tags = self.find_tags_in_tit_abs(tasklist, last_abstract, last_par_id,
                                                     last_title if last_par_id == 0 else PARAGRAPH_TITLE_DUMMY)
                    tag_json[last_out_doc_id].update(tags=tags)
                    tasklist.clear()
                last_art_id = tag.document_id
                if doc_id != last_doc_id:  # New document: set FileReader if source is file
                    last_translation = self.get_translation_by_docid(doc_id)
                    if '.json' in last_translation.source:
                        current_filereader = FileReader(self.get_get_sourcefile_by_docid(doc_id))
                        last_title = current_filereader.title
                    out_doc_id, doc_dict = self.create_document_json(doc_id)
                    last_out_doc_id = out_doc_id
                    tag_json[out_doc_id] = doc_dict
                    last_doc_id = doc_id
                if '.csv' in last_translation.source:  # New paragraph + source is csv
                    title, abstract, md5 = self.meta.get_doc_content(last_translation.source_doc_id, True)
                    last_title, last_abstract = title, abstract
                    source_hash = md5
                elif '.json' in last_translation.source:
                    abstract = current_filereader.get_paragraph(par_id)
                    if par_id == 0 and not abstract:
                       _, abstract, _ = self.meta.get_doc_content(last_translation.source_doc_id)
                    last_abstract = abstract


            tasklist.append(tag)
        return tag_json

    def export(self, tag_types, only_abstract=False):
        self.logger.info("Starting export...")
        tag_json = self.create_tag_json(tag_types)
        with open(self.out_file, "w+") as f:
            json.dump(tag_json, f, indent=3)

        if only_abstract:
            abstract_json = {}
            for key in tag_json.keys():
                document_json = {}
                tag_json[key].update(tags=[tag for tag in tag_json[key]['tags'] if tag['location']['par']==0])
                if not tag_json[key]['tags']:
                    tag_json.pop(key)
            with open(self.out_file + ".abstract", "w+") as f:
                json.dump(tag_json, f, indent=3)







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


def export(out_fn, tag_types, json_root, info_file, document_ids=None, collection=None, logger=logging,
           tag_buffer=TAG_BUFFER_SIZE, only_abstract=False):
    logger.info("Beginning export...")
    if document_ids is None:
        document_ids = []
    else:
        logger.info('Using {} ids for a filter condition'.format(len(document_ids)))

    session = Session.get()
    tag_query = create_tag_query(session, collection, document_ids, tag_types, tag_buffer)




    logger.info('loading file locations...')
    files = glob(f"{json_root}/**/*", recursive=True)
    file_dir = {os.path.basename(f).split(".")[0]: f for f in files}
    logger.info('loading info csv...')
    with open(info_file) as info:
        info_reader = csv.reader(info, delimiter='\t')
        next(info_reader)
        logger.info('creating doc_id - file dict...')
        file_dict = {int(art_id): file_dir.get(doc_id, None) for art_id, doc_id in info_reader}
    logger.info(f"Processing {len(file_dict)} documents")
    document_count = 0
    start_time = datetime.now()
    logger.info('Starting to search for tags.')
    tag_json = {}
    found = 0
    not_found = 0
    shaky = 0
    old_art_doc_id = None
    old_art_par_id = None
    generate_new_index = False
    for tag in tag_query:
        try:
            cur_art_doc_id = tag.document_id - tag.document_id % NEXT_DOCUMENT_ID_OFFSET
            cur_art_par_id = tag.document_id % NEXT_DOCUMENT_ID_OFFSET
            if cur_art_doc_id != old_art_doc_id:
                old_art_doc_id = cur_art_doc_id
                file = file_dict[cur_art_doc_id]
                doc_id = os.path.basename(file)
                tag_json[doc_id] = []
                reader = FileReader(file)
                print_progress_with_eta('searching', document_count, len(file_dict), start_time, logger=logger, print_every_k=100)
                document_count +=1
                #print(document_count)
                generate_new_index = True
            if generate_new_index or cur_art_par_id != old_art_par_id:
                if only_abstract and cur_art_par_id > 0:
                    continue
                logger.debug(f"{cur_art_doc_id}:{cur_art_par_id} -> {file}, {reader.title})")
                logger.debug(f"{reader.get_paragraph(cur_art_par_id)}")
                generate_new_index = False
                old_art_par_id=cur_art_par_id
                if cur_art_par_id == 0:
                    san_index = create_sanitized_index(reader.abstract)
                else:
                    san_index = create_sanitized_index(reader.get_paragraph(cur_art_par_id))
                title_index = create_sanitized_index(reader.title)

                text_offset = len(reader.title) +3 if cur_art_par_id==0 else len(" SECTION") + 2
            if tag.start < text_offset:
                par = 0 #title
                js_start = title_index[tag.start]  #- title_offset
                js_end = title_index[tag.end] #- title_offset
            else:
                par = cur_art_par_id + 1
                js_start = san_index[tag.start - text_offset]
                js_end = san_index[tag.end - text_offset]
            logger.debug(f"{tag.ent_str}: {tag.start}-{tag.end} -> {js_start} - {js_end} "
                  f"({reader.get_paragraph(cur_art_par_id)[js_start-10:js_start]}|"
                  f"{reader.get_paragraph(cur_art_par_id)[js_start:js_end]}|"
                  f"{reader.get_paragraph(cur_art_par_id)[js_end:js_end + 10]})")
            tag_dict = {
                "location": {
                    "paragraph": par,
                    "start": js_start,
                    "end": js_end
                },
                "entity_str": tag.ent_str,
                "entity_type": tag.ent_type,
                "entity_id": tag.ent_id,

            }
            if tag_dict:
                if not doc_id in tag_json:
                    tag_json[doc_id] = []
                tag_json[doc_id].append(tag_dict)
            found+=1
        except:
            logger.debug(f"Tag {tag.id} ({tag.ent_str}) not found")
            not_found += 1
            continue

    logger.info(f"Done searching. Tags processed: {not_found + found}, "
                f"Tags not found: {100*not_found/(not_found + found)}%,")
    logger.info(f"Writing json to {out_fn}")
    with open(out_fn, "w+") as out:
        json.dump(tag_json, out, indent=3)

def create_sanitized_index(content:str):
    """
    Takes a string and outputs a list to converts from sanitized index to non-sanitized index.
    :param content: The string to be indexed
    :return: List sanitized index -> non sanitized index
    """
    san_index = []
    for not_san_i, char in enumerate(content):
        if not ILLEGAL_CHAR.match(char):
            san_index.append(not_san_i)
    return san_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("jsonroot")
    parser.add_argument("metafile")
    parser.add_argument("-a", "--only-abstract", action='store_true')
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


if __name__ == "__main__":
    main()
