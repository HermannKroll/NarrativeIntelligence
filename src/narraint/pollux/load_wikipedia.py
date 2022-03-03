import argparse

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.backend.models import Document
from kgextractiontoolbox.progress import Progress
from narraint.document.translation.translate_wiki import WikiLoader

def load(collection, extractor_dump, tsv_path):
    documents = []
    loader = WikiLoader(collection, tsv_path)
    progress = Progress
    for sdoc in loader.read_sourced_documents(extractor_dump):
        documents.append(dict(
            id=sdoc.doc.id,
            title=sdoc.doc.title,
            abstract=sdoc.doc.abstract,
            collection=collection
        ))
    session = Session.get()
    Document.bulk_insert_values_into_table(session=session, values=documents)



def main():
    parser = argparse.ArgumentParser("load wikipedia docs")
    parser.add_argument("input", help="directory containing extractor dump")
    parser.add_argument("-c", "--collection")
    parser.add_argument("-t", "--tsv-path")
    args = parser.parse_args()
    load(args.collection, args.input, args.tsv_path)

if __name__ == '__main__':
    main()