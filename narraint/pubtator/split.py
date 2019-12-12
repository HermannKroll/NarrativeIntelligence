import os
from argparse import ArgumentParser

from narraint.pubtator.regex import DOCUMENT_ID


def write_content(content, out_dir):
    doc_id = DOCUMENT_ID.findall(content)
    if doc_id:
        with open(os.path.join(out_dir, "{}.txt".format(doc_id[0])), "w") as f:
            f.write(content)
    else:
        raise ValueError("No ID for {}".format(content))


def split(filename, out_dir):
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    with open(filename) as fin:
        content = ""
        for line in fin:
            if line.strip():
                content += line
            else:
                write_content(content, out_dir)
                content = ""


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubTator file", metavar="FILE")
    parser.add_argument("output", help="Directory", metavar="DIR")
    args = parser.parse_args()
    split(args.input, args.output)


if __name__ == "__main__":
    main()
