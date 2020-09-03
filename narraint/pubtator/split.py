import os
from argparse import ArgumentParser

from narraint.pubtator.regex import DOCUMENT_ID
from narraint.pubtator.extract import read_pubtator_documents


def write_content(content, out_dir, document_prefix=""):
    doc_ids = DOCUMENT_ID.findall(content)
    if doc_ids:
        filename = f"{document_prefix}{doc_ids[0]}.txt" if doc_ids[0] == doc_ids[-1] \
            else f"{document_prefix}{doc_ids[0]}-{doc_ids[-1]}.txt"
        with open(os.path.join(out_dir, filename), "w") as f:
            f.write(content + '\n')  # pubtator files must be terminated by an \n
    else:
        raise ValueError("No ID for {}".format(content))


def split(filename, out_dir, batch_size=1, logger=None, document_prefix=""):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    docs_in_batch = 0
    if logger: logger.debug('splitting file (batch size is {})...'.format(batch_size))
    doc_group_content = []
    for doc_content in read_pubtator_documents(filename):
        docs_in_batch += 1
        doc_group_content.append(doc_content)
        # FIXME: Ensure that last batch possibly being smaller than the batch size is written anyway
        if docs_in_batch >= batch_size:
            write_content('\n'.join(doc_group_content), out_dir, document_prefix)
            doc_group_content = []
            docs_in_batch = 0
    if logger: logger.debug('finished')


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubTator file", metavar="FILE")
    parser.add_argument("output", help="Directory", metavar="DIR")
    parser.add_argument("-b", "--batch", type=int, help="Size of a batch", metavar="N", default=1)
    args = parser.parse_args()
    split(args.input, args.output, args.batch)


if __name__ == "__main__":
    main()
