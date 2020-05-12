import argparse
import logging
import csv
import os
from datetime import datetime
from glob import glob

import json

from narraint.backend.database import Session
from narraint.backend.export import create_tag_query, TAG_BUFFER_SIZE
from narraint.entity import enttypes
from narraint.entity.enttypes import TAG_TYPE_MAPPING
from narraint.pubtator.regex import ILLEGAL_CHAR
from narraint.progress import print_progress_with_eta
from narraint.pubtator.translation.cord19m2fulltexts import NEXT_DOCUMENT_ID_OFFSET

TITLE = "title"
ABSTRACT = "abstract"
BODY = "body"

MAX_SCAN_WIDTH = 1000

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
        return f'{self.paper_id}: {self.abstract[:200]}... {self.body_texts[0]}...'

    def get_paragraph(self, art_par_id):
        """
        Get the text of the abstract or the full text paraphs
        :param art_par_id: 0 refers to abstract, >=1 to full text paragraphs
        :return:
        """
        return self.body_texts[art_par_id-1]

    def get_json_location(self, full_str_index):
        """
        find location of full_str index in json file
        :param full_str_index: the index of the full_str to be found in the json file
        :return: (sec, par, ind) - Section (title, abstract or body), paragraph-nr and local index within paragraph. 
            If section is title, par is always 0
        """
        if full_str_index > self.body_start():
            section = BODY
            *_, paragraph_nr = (nr for nr, p in enumerate(self.body_paragraph_pointers) if
                                p <= full_str_index - self.body_start())  # last nr of generator
            local_index = full_str_index - self.body_paragraph_pointers[paragraph_nr]
        elif full_str_index > self.abstract_start():
            section = ABSTRACT
            *_, paragraph_nr = (nr for nr, p in enumerate(self.abstract_paragraph_pointers) if
                                p < full_str_index - self.abstract_start())
            local_index = full_str_index - self.abstract_paragraph_pointers[paragraph_nr]
        else:
            section = TITLE
            paragraph_nr = 0
            local_index = full_str_index
        return section, paragraph_nr, local_index


def export(out_fn, tag_types, json_root, info_file, document_ids=None, collection=None, logger=logging,
           tag_buffer=TAG_BUFFER_SIZE):
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
    art_id = None
    tag_json = {}
    tagtype_offset = 0
    current_tagtype = None
    found = 0
    not_found = 0
    shaky = 0
    old_art_doc_id = None
    old_art_par_id = None
    generate_new_index = False
    for tag in tag_query:
        cur_art_doc_id = tag.document_id - tag.document_id % NEXT_DOCUMENT_ID_OFFSET
        cur_art_par_id = tag.document_id % NEXT_DOCUMENT_ID_OFFSET
        if cur_art_doc_id != old_art_doc_id:
            old_art_doc_id = cur_art_doc_id
            file = file_dict[cur_art_doc_id]
            doc_id = os.path.basename(file)
            tag_json[doc_id] = []
            reader = FileReader(file)
            tagtype_offset = 0
            logger.debug(f"{art_id} {file})")
            print_progress_with_eta('searching', document_count, len(file_dict), start_time, logger=logger, print_every_k=100)
            document_count +=1
            generate_new_index = True
        if generate_new_index or cur_art_par_id != old_art_par_id:
            generate_new_index = False
            if cur_art_par_id == 0:
                san_index = create_sanitized_index(reader.abstract)
            else:
                san_index = create_sanitized_index(reader.get_paragraph(cur_art_par_id))
            title_index = create_sanitized_index(reader.title)
            title_offset = len(f"{tag.document_id}|t| ")
            text_offset = len(f"{tag.document_id}|t| {reader.title}\n{tag.document_id}|a| ")
        if tag.start < text_offset:
            par = 0 #title
            js_start = tag.start - title_offset
            js_end = tag.end - title_offset
        else:
            par = cur_art_par_id + 1
            js_start = tag.start - text_offset
            js_end = tag.end - text_offset

        tag_dict = {
            "location": {
                "paragraph": par,
                "start": js_start,
                "end": js_end
            },
            "tag_str": tag.ent_str,
            "tag_type:": tag.ent_type,
            "identifier": tag.ent_id,

        }
        tag_json[doc_id].append(tag_dict)

    logger.info(f"Done searching. Tags processed: {not_found + found}, "
                f"Tags not found: {100*not_found/(not_found + found)}%,"
                f"Tags shakey: {100*shaky/(not_found + found)}%")
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
    current_sanitized_i = 0
    for not_san_i, char in enumerate(content):
        if not ILLEGAL_CHAR.match(char):
            san_index[current_sanitized_i]=not_san_i
            current_sanitized_i += 1
    return san_index



def search_sanitized(base_str, search_str, start_index):
    """
    search for sanitized substring in unsanitized base string
    :param base_str: the unsanitized string to seach in
    :param search_str: the sanitized string to be found
    :param start_index: only search right of offset
    :return: (start, end) of string in unsanitized base_str
    """
    length = len(search_str)
    for offset in range(start_index, min(start_index + max(MAX_SCAN_WIDTH, len(search_str) // 100), len(base_str) - 1)):
        compare_str = ""
        text_pointer = offset
        while not text_pointer >= len(base_str) and len(compare_str) < length:
            if not ILLEGAL_CHAR.match(base_str[text_pointer]):
                compare_str += base_str[text_pointer].lower()
            text_pointer += 1
        # print(compare_str)
        if compare_str == search_str.lower():
            return offset, text_pointer
    else:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("jsonroot")
    parser.add_argument("infofile")
    parser.add_argument("--ids", nargs="*", metavar="DOC_ID")
    parser.add_argument("--idfile", help='file containing document ids (one id per line)')
    parser.add_argument("-c", "--collection", help="Collection(s)", default=None)
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")
    parser.add_argument("-l", "--loglevel", default="INFO")
    args = parser.parse_args()

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
    export(args.output, tag_types, args.jsonroot, args.infofile, ids, args.collection)


if __name__ == "__main__":
    main()
