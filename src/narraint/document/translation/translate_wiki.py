import json
import logging

import argparse

import glob
import pandas as pd
from typing import Union
from pathlib import Path

from kgextractiontoolbox.document import load_document
from kgextractiontoolbox.document.document import TaggedDocument
from kgextractiontoolbox.progress import Progress
from narraint.pollux.doctranslation import SourcedDocument, DocumentTranslationLoader


class WikiLoader(DocumentTranslationLoader):
    def __init__(self, collection, url_list_path):
        super().__init__(collection)
        self.url_set = WikiLoader.load_url_set(url_list_path)
        pass

    @staticmethod
    def load_url_set(url_list_path):
        doc = pd.read_csv(url_list_path, sep='\t')
        return {l.strip().lower() for l in doc['itemLabel']} #| {n for s in doc['labels'] for n in s.split(";")}

    # make this an overridable class and include it into toolbox
    def read_sourced_documents(self, file: Union[Path, str]):
        if not type(file) == Path:
            file = Path(file)
        for single_file in glob.glob(f'{file}/**/*'):
            with open(single_file) as f:
                for line in f:
                    json_content = json.loads(line)
                    if json_content['title'].strip().lower() in self.url_set:
                        doc = TaggedDocument(id=int(json_content["id"]), title=json_content['title'], abstract=json_content['text'].encode('utf-8').decode(
                            'utf-8'))
                        yield SourcedDocument(json_content["id"], single_file, doc)

    def count_documents(self, file: Union[Path, str]):
        #count = 0
        #for line in open(file): count += 1
        return 2502





def main():
    """
    Run the document translation, insert translation entries into the document_translation table,
    export documents to a json file and load them into the database if -l flag is set.
    :param doctrans_args: keyword arguments for doctranslation
    :param doctranslation_subclass: The subclass of the DocumentTranlationLoader capable of reading SourcedDocuments from
    the used third-party format
    :param args: command line arguments
    :return: None
    """

    parser = argparse.ArgumentParser("load wiki documents")
    parser.add_argument("input", help="ijson input file")
    parser.add_argument("output", help="output json file")
    parser.add_argument("-c", "--collection", required=True, help="document collection")
    parser.add_argument("-d", "--diff", action="store_true", help="only process documents with new/changed md5 hash")
    parser.add_argument("-l", "--load", action="store_true", help="load document contents into document table")
    parser.add_argument("-n", "--limit", type=int, help="Only exctract that many documents from source doc")
    parser.add_argument("-u", "--url-list", type=str, help="Path to tsv containing urls in 'article' column")
    args = parser.parse_args()

    loader = WikiLoader(args.collection, args.url_list)
    logging.basicConfig(level="INFO")
    logging.info("Pollux document translation")
    logging.debug(f"Input file: {args.input}")
    logging.debug(f"Output file: {args.output}")
    logging.info("Counting documents...")
    count = loader.count_documents(args.input)
    logging.info(f"Found {count} documents.")
    prog = Progress(total=(args.limit or count), text="Translating")
    proc_docs = loader.translate(args.input, args.output, diff=args.diff, prog_logger=prog, limit=args.limit)
    logging.info(f"Processed {proc_docs} new or changed documents.")
    if args.load:
        load_document.main([args.output, "-c", args.collection])


if __name__ == '__main__':
    main()
