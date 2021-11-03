import datetime
import hashlib
import json
import logging
from collections import namedtuple
from dataclasses import dataclass
from operator import and_
from typing import Union, NamedTuple
import ijson
import argparse
from pathlib import Path

import narraint.backend.database as db
import narrant.backend.load_document as load_document
from sqlalchemy import func, select
from kgextractiontoolbox.document.document import TaggedDocument
from narraint.backend.models import DocumentTranslation
from narrant.progress import Progress


def main(args=None):
    parser = argparse.ArgumentParser("load pollux documents")
    parser.add_argument("input", help="ijson input file")
    parser.add_argument("output", help="output json file")
    parser.add_argument("-c", "--collection", required=True, help="document collection")
    parser.add_argument("-d", "--diff", action="store_true", help="only process documents with new/changed md5 hash")
    parser.add_argument("-l", "--load", action="store_true", help="load document contents into document table")
    args = parser.parse_args()

    loader = PolluxLoader(args.collection)
    logging.info("Pollux document translation")
    logging.debug(f"Input file: {args.input}")
    logging.debug(f"Output file: {args.output}")
    logging.info("Counting documents...")
    count = loader.count_documents(args.input)
    logging.info(f"Found {count} documents.")
    prog = Progress(total=count, text="Translating")
    proc_docs = loader.translate(args.input, args.output, diff=args.diff, prog_logger=prog)
    logging.info(f"Processed {proc_docs} new or changed documents.")
    if args.load:
        load_document.main([args.output, "-c", args.collection])
    #loader.read_tagged_documents(args.input)

@dataclass
class SourcedDocument:
    source_id: str
    source: str
    doc: TaggedDocument



class ConversionLoader:
    def __init__(self, collection):
        self.session = db.SessionExtended.get()
        self.collection = collection
        self.current_art_id = self.poll_hightest_art_id() + 1
        self.insertion_time = datetime.datetime.now()

    def poll_hightest_art_id(self):
        result = self.session.execute(
            select(
                func.max(DocumentTranslation.document_id)
            ).where(DocumentTranslation.document_collection == self.collection)
        )
        return [r for r in result][0][0] or 0

    def check_md5_changed(self, doc: SourcedDocument):
        result = self.session.execute(
            select(
                DocumentTranslation.md5
            ).where(and_(
                DocumentTranslation.document_collection == self.collection,
                DocumentTranslation.source_doc_id == doc.source_id
            ))
        )
        result = [r for r in result]
        if not result:
            return True
        else:
            return result[0][0] != self.get_md5(doc)

    def create_translation_entry(self, sdoc:SourcedDocument):
        sdoc.doc.id = self.current_art_id
        self.current_art_id += 1
        return {
            "document_id": sdoc.doc.id,
            "document_collection": self.collection,
            "source_doc_id": sdoc.source_id,
            "md5": self.get_md5(sdoc),
            "source": sdoc.source,
            "date_inserted": self.insertion_time
        }

    def translate(self, infile: Union[Path, str], outfile: Union[Path, str], insert_every=100, diff=False, prog_logger: Progress=None):
        translations = []
        processed_docs = 0
        with open(outfile, "w+") as outf:
            prog_logger.start_time()
            outf.write("[")
            first = True
            for n, sdoc in enumerate(self.read_sourced_documents(infile)):
                if not diff or self.check_md5_changed(sdoc):
                    translations.append(self.create_translation_entry(sdoc))
                    if not first:
                        outf.write(",\n")
                    else:
                        first=False
                    outf.write(json.dumps(sdoc.doc.to_dict()))
                    processed_docs +=1
                    if len(translations) > 100:
                        self.flush(translations)
                        translations = []
                prog_logger.print_progress(n)
            self.flush(translations)
            outf.write("]")
            prog_logger.done()
            return processed_docs

    def flush(self, translations):
        self.session.bulk_insert_mappings(DocumentTranslation, translations)
        self.session.commit()

    @staticmethod
    def get_md5(sdoc: SourcedDocument):
        return hashlib.md5((sdoc.doc.title+sdoc.doc.abstract).encode('unicode_escape')).hexdigest()

    def read_sourced_documents(self, file: Union[Path, str]):
        raise NotImplementedError()

    def count_documents(self, file: Union[Path, str]):
        raise NotImplementedError()

class PolluxLoader(ConversionLoader):
    def __init__(self, collection):
        super().__init__(collection)

    # make this an overridable class and include it into toolbox
    def read_sourced_documents(self, file: Union[Path, str]):
        if not type(file) == Path:
            file = Path(file)
        with open(file) as f:
            for line in f:
                content = json.loads(line)
                source_id = content["id"]
                source = file.name
                title = content["title"].encode('unicode_escape').decode('unicode_escape')
                for n, abstract in enumerate(content["abstracts"]):
                    doc = TaggedDocument(title=title, abstract=abstract['value'].encode('unicode_escape').decode(
                        'unicode_escape'))
                    yield SourcedDocument(f"{source_id}:{n}", source, doc)

    def count_documents(self, file: Union[Path, str]):
        count = 0
        for line in open(file): count += 1
        return count



if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    main()
    # 13cd3a58fa8cd5360f252c766d305248
    # 13cd3a58fa8cd5360f252c766d305248