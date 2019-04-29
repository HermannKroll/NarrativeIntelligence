import argparse
import os
import re
import sys
from argparse import ArgumentParser

from preprocessing.tag import merge_pubtator_files


def batch(iterable, n=1):
    """
    https://stackoverflow.com/questions/8290397/how-to-split-an-iterable-in-constant-size-chunks
    """
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def required_length(nmin, nmax):
    """
    https://stackoverflow.com/questions/4194948/python-argparse-is-there-a-way-to-specify-a-range-in-nargs
    """

    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not nmin <= len(values) <= nmax:
                msg = 'argument "{f}" requires between {nmin} and {nmax} arguments'.format(
                    f=self.dest, nmin=nmin, nmax=nmax)
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)

    return RequiredLength


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
                f.write(document + "\n\n")


# TODO: Add doc
def concat(input_dir, output_file, batch_size=None):
    files = []
    for fn in os.listdir(input_dir):
        if fn.endswith(".txt"):
            with open(os.path.join(input_dir, fn)) as f:
                files.append(f.read())

    if batch_size:
        basename = ".".join(output_file.split(".")[:-1])
        ext = output_file.split(".")[-1]
        for idx, b in enumerate(batch(files, int(batch_size))):
            with open("{}.{:02d}.{}".format(basename, idx, ext), "w") as f:
                f.writelines(b)
    else:
        with open(output_file, "w") as f:
            f.writelines(files)


# TODO: Add doc
def main():
    parser = ArgumentParser()
    parser.add_argument("--count", help="Count the number of PMC documents in a PubTator file", metavar="FILE")
    parser.add_argument("--split", nargs=2, help="Split the PubTator file into its contained documents",
                        metavar=("FILE", "OUTPUT_DIR"))
    parser.add_argument("--concat", nargs="+",
                        help="Concat PubTator files of directory into a single file (DIR, OUTPUT, BATCH_SIZE)",
                        action=required_length(2, 3))
    parser.add_argument("--cdg-merge", nargs=3, metavar=("FILE1", "FILE2", "OUTPUT_FILE"))
    args = parser.parse_args()

    if args.count:
        print("Found {} distinct documents.".format(count_documents(args.count)))

    if args.split:
        sys.stdout.write("Begin splitting ...")
        sys.stdout.flush()
        split(args.split[0], args.split[1])
        sys.stdout.write(" done\n")

    if args.concat:
        sys.stdout.write("Begin merging ...")
        sys.stdout.flush()
        concat(args.merge[0], args.merge[1], args.merge[2] if len(args.merge) == 3 else None)
        sys.stdout.write(" done\n")

    if args.cdg_merge:
        merge_pubtator_files(args.cdg_merge[0], args.cdg_merge[1], args.cdg_merge[2])


if __name__ == "__main__":
    main()
