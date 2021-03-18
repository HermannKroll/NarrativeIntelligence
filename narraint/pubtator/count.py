import os
from argparse import ArgumentParser

from narraint.pubtator.regex import DOCUMENT_ID, TAG_DOCUMENT_ID


def get_document_ids(path: str):
    ids = set()
    if os.path.isdir(path):
        for fn in os.listdir(path):
            if fn.endswith(".txt"):
                ids.update(get_document_ids(os.path.join(path, fn)))
    else:
        with open(path) as f:
            for line in f:
                ids.update(int(x) for x in DOCUMENT_ID.findall(line))
                # search only for tag ids if no title lines were found before
                if len(ids) == 0:
                    ids.update(int(x) for x in TAG_DOCUMENT_ID.findall(line))
    return ids


def count_documents(path):
    """
    Count PubTator documents in a directory or in a file.
    :param path: Path to directory or file
    :return: Number of distinct document IDs
    """
    return len(get_document_ids(path))


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubTator file", metavar="FILE")
    args = parser.parse_args()
    print("Found {} documents".format(count_documents(args.input)))


if __name__ == "__main__":
    main()
