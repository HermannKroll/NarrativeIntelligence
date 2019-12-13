import os
from argparse import ArgumentParser

from narraint.pubtator.regex import DOCUMENT_ID
from narraint.tools import count_lines


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
    line_count = count_lines(filename)
    with open(filename) as fin:
        content = ""
        docs_in_batch = 0
        for idx, line in enumerate(fin):
            if line.strip():
                content += line
            else:
                docs_in_batch += 1
                content += "\n"
                if docs_in_batch >= batch_size or idx == line_count - 1:
                    write_content(content, out_dir)
                    content = ""
                    docs_in_batch = 0


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubTator file", metavar="FILE")
    parser.add_argument("output", help="Directory", metavar="DIR")
    parser.add_argument("-b", "--batch", type=int, help="Size of a batch", metavar="N", default=1)
    args = parser.parse_args()
    split(args.input, args.output, args.batch)


if __name__ == "__main__":
    main()
