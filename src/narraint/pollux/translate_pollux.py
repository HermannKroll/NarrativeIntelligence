import datetime
import hashlib
import json
from collections import namedtuple
from dataclasses import dataclass
from operator import and_
from typing import Union, NamedTuple
import ijson
import argparse
from pathlib import Path

import narraint.backend.database as db
from sqlalchemy import func, select
from kgextractiontoolbox.document.document import TaggedDocument
from narraint.backend.models import DocumentTranslation


def main(args=None):
    parser = argparse.ArgumentParser("load pollux documents")
    parser.add_argument("input", help="ijson input file")
    parser.add_argument("output", help="output json file")
    parser.add_argument("-c", "--collection", required=True, help="document collection")
    args = parser.parse_args()

    loader = PolluxLoader(args.collection)
    loader.translate(args.input, args.output)
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
        return not result or result != self.get_md5(doc)

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

    def translate(self, infile: Union[Path, str], outfile: Union[Path, str], insert_every=100):
        translations = []
        with open(outfile, "w+") as outf:
            outf.write("[")
            for sdoc in self.read_sourced_documents(infile):
                if self.check_md5_changed(sdoc):
                    translations.append(self.create_translation_entry(sdoc))
                    outf.write(json.dumps(sdoc.doc.to_dict()) + ",\n")
                    if len(translations) > 100:
                        self.flush(translations)
                        translations = []
            self.flush(translations)

    def flush(self, translations):
        self.session.bulk_insert_mappings(DocumentTranslation, translations)
        self.session.commit()

    @staticmethod
    def get_md5(sdoc: SourcedDocument):
        return hashlib.md5((sdoc.doc.title+sdoc.doc.abstract).encode('unicode_escape')).hexdigest()

    def read_sourced_documents(self, file: Union[Path, str]):
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





if __name__ == '__main__':
    main()