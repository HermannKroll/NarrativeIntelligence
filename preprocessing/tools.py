import os
import re
import sys
from argparse import ArgumentParser

# TODO: Add doc
from tagging.base import merge_result_files, finalize_dir


# def batch(iterable, n=1):
#     """
#     https://stackoverflow.com/questions/8290397/how-to-split-an-iterable-in-constant-size-chunks
#     """
#     l = len(iterable)
#     for ndx in range(0, l, n):
#         yield iterable[ndx:min(ndx + n, l)]
#
#
# def required_length(nmin, nmax):
#     """
#     https://stackoverflow.com/questions/4194948/python-argparse-is-there-a-way-to-specify-a-range-in-nargs
#     """
#
#     class RequiredLength(argparse.Action):
#         def __call__(self, parser, args, values, option_string=None):
#             if not nmin <= len(values) <= nmax:
#                 msg = 'argument "{f}" requires between {nmin} and {nmax} arguments'.format(
#                     f=self.dest, nmin=nmin, nmax=nmax)
#                 raise argparse.ArgumentTypeError(msg)
#             setattr(args, self.dest, values)
#
#     return RequiredLength


def get_documents_in_file(filename):
    ids = set()
    with open(filename) as f:
        for line in f:
            matches = re.findall(r"^(\d+).*\n$", line, re.DOTALL)
            if matches:
                ids |= {int(matches[0])}
    return ids


# TODO: Add doc
def count_documents(filename):
    ids = set()
    if os.path.isdir(filename):
        for fn in os.listdir(filename):
            if fn.endswith(".txt"):
                ids |= get_documents_in_file(os.path.join(filename, fn))
    else:
        ids = get_documents_in_file(filename)
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
def concat(input_dir, output_file):
    sys.stdout.write("Concatenating files ...")
    sys.stdout.flush()
    files = []
    for fn in sorted(os.listdir(input_dir)):
        if fn.endswith(".txt"):
            with open(os.path.join(input_dir, fn)) as f:
                files.append(f.read())

    with open(output_file, "w") as f:
        f.writelines(files)
    sys.stdout.write(" done.\n")


# TODO: Add doc
def main():
    parser = ArgumentParser()
    parser.add_argument("--count", help="Count the number of PMC documents in a PubTator file", metavar="FILE")
    parser.add_argument("--split", nargs=2, help="Split the PubTator file into its contained documents",
                        metavar=("FILE", "OUTPUT_DIR"))
    parser.add_argument("--concat", nargs=2,
                        help="Concat PubTator files of directory into a single file (DIR, OUTPUT)")
    parser.add_argument("--merge", nargs="*", metavar="FILE")
    parser.add_argument("--out", metavar="OUTPUT_FILE")
    parser.add_argument("--translation-dir", metavar="TRANSLATION_DIR")
    parser.add_argument("--finalize-dir", metavar=("DIR", "FILE"), nargs=2)
    args = parser.parse_args()

    if args.count:
        print("Found {} distinct documents.".format(count_documents(args.count)))

    if args.split:
        sys.stdout.write("Begin splitting ...")
        sys.stdout.flush()
        split(args.split[0], args.split[1])
        sys.stdout.write(" done\n")

    if args.concat:
        sys.stdout.write("Begin concatenation...")
        sys.stdout.flush()
        concat(args.concat[0], args.concat[1])
        sys.stdout.write(" done\n")

    if args.merge and args.translation_dir and args.out:
        merge_result_files(args.translation_dir, args.out, *args.merge)

    if args.finalize_dir:
        finalize_dir(args.finalize_dir[0], args.finalize_dir[1])


if __name__ == "__main__":
    main()
