import os
from argparse import ArgumentParser

from narraint.pubtator.regex import DOCUMENT_ID
from narraint.pubtator.extract import read_pubtator_documents


def write_content(content, out_dir):
    doc_ids = DOCUMENT_ID.findall(content)
    if doc_ids:
        filename = f"{doc_ids[0]}.txt" if doc_ids[0] == doc_ids[-1] else f"{doc_ids[0]}-{doc_ids[-1]}.txt"
        with open(os.path.join(out_dir, filename), "w") as f:
            f.write(content)
    else:
        raise ValueError("No ID for {}".format(content))


def split(filename, out_dir, batch_size=1):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    docs_in_batch = 0
    print('splitting file (batch size is {})...'.format(batch_size))
    for doc_content in read_pubtator_documents(filename):
        docs_in_batch += 1
        if docs_in_batch >= batch_size:
            write_content(doc_content, out_dir)
            docs_in_batch = 0
    print('finished')


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubTator file", metavar="FILE")
    parser.add_argument("output", help="Directory", metavar="DIR")
    parser.add_argument("-b", "--batch", type=int, help="Size of a batch", metavar="N", default=1)
    args = parser.parse_args()
    split(args.input, args.output, args.batch)


if __name__ == "__main__":
    main()
