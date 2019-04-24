import os
import re
import sys
from argparse import ArgumentParser


# TODO: Add doc
def count_documents(filename):
    ids = set()
    with open(filename) as f:
        for line in f:
            matches = re.findall(r"^(\d+).*\n$", line, re.DOTALL)
            if matches:
                ids |= {int(matches[0])}
    return len(ids)


# TODO: Add doc
def split(input_file, output_dir):
    with open(input_file) as f:
        content = f.read()
    documents = content.split("\n\n")
    for document in documents:
        if document:
            did = document[0:document.index("|")]
            with open(os.path.join(output_dir, "PMC{}.txt".format(did)), "w") as f:
                f.write(document + "\n")


# TODO: Add doc
def merge(input_dir, output_file):
    files = []
    for fn in os.listdir(input_dir):
        if fn.endswith(".txt"):
            with open(os.path.join(input_dir, fn)) as f:
                files.append(f.read() + "\n")
    with open(output_file, "w") as f:
        f.writelines(files)


# TODO: Add doc
def main():
    parser = ArgumentParser()
    parser.add_argument("--count", help="Count the number of PMC documents in a PubTator file", metavar="FILE")
    parser.add_argument("--split", nargs=2, help="Split the PubTator file into its contained documents",
                        metavar=("FILE", "OUTPUT_DIR"))
    parser.add_argument("--merge", nargs=2, help="Merge PubTator files of directory into a single file",
                        metavar=("INPUT_DIR", "OUTPUT_FILE"))
    args = parser.parse_args()

    if args.count:
        print("Found {} distinct documents.".format(count_documents(args.count)))

    if args.split:
        sys.stdout.write("Begin splitting ...")
        sys.stdout.flush()
        split(args.split[0], args.split[1])
        sys.stdout.write(" done\n")

    if args.merge:
        sys.stdout.write("Begin merging ...")
        sys.stdout.flush()
        merge(args.merge[0], args.merge[1])
        sys.stdout.write(" done\n")


if __name__ == "__main__":
    main()
