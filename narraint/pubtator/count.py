import os
from argparse import ArgumentParser

from narraint.pubtator.regex import DOCUMENT_ID


def count_documents(path):
    """
    Count PubTator documents in a directory or in a file.
    :param path: Path to directory or file
    :return: Number of distinct document IDs
    """
    count = 0
    if os.path.isdir(path):
        for fn in os.listdir(path):
            if fn.endswith(".txt"):
                count += count_documents(os.path.join(path, fn))
    else:
        with open(path) as f:
            content = f.read()
        count = len(set(DOCUMENT_ID.findall(content)))
    return count


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubTator file", metavar="FILE")
    args = parser.parse_args()
    print("Found {} documents".format(count_documents(args.count)))


if __name__ == "__main__":
    main()
