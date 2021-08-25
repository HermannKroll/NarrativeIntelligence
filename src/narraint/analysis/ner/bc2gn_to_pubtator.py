import os

from narraint.config import DATA_DIR
from narrant.pubtator.document import TaggedDocument

BC2GN_SRC_DIR = os.path.join(DATA_DIR, "NER/biocreative2normalization/trainingData/")
output = os.path.join("/home/jan/bc2GNtraining.pubtator")


def read_pubtator_documents_from_bc2gn_dir(dir: str):
    for fn in os.listdir(dir):
        id = os.path.basename(fn)[:-4]
        if fn == "training.genelist":
            continue
        with open(os.path.join(dir, fn)) as f:
            title = f.readline()
            f.readline()
            abstract = f.readline()
        doc = TaggedDocument(id=id, title=title, abstract=abstract, ignore_tags=True)
        yield doc


def main():
    with open(output, "w+") as out:
        for doc in read_pubtator_documents_from_bc2gn_dir(BC2GN_SRC_DIR):
            out.write(str(doc))


if __name__ == '__main__':
    main()
