import os
import re
import sys
from argparse import ArgumentParser


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


# TODO: Add doc
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


# # TODO: Add doc
# def read_pubtator_file(filename):
#     docs = {}
#     with open(filename) as f:
#         for line in f:
#             if line.strip():
#                 did = re.findall(r"^\d+", line)[0]
#                 if did not in docs:
#                     docs[did] = dict(title="", abstract="", tags=[])
#                 if title_pattern.match(line):
#                     docs[did]["title"] = line.strip()
#                 elif abstract_pattern.match(line):
#                     docs[did]["abstract"] = line.strip()
#                 else:
#                     docs[did]["tags"] += [line.strip()]
#
#     return docs
#
#
# # TODO: Add doc
# def merge_pubtator_files(file1, file2, output):
#     d1 = read_pubtator_file(file1)
#     d2 = read_pubtator_file(file2)
#
#     ids = set(d1.keys()) | set(d2.keys())
#
#     with open(output, "w") as f:
#         for did in ids:
#             if did in d1 and did not in d2:
#                 title = d1[did]["title"]
#                 abstract = d1[did]["abstract"]
#                 tags = d1[did]["tags"]
#             elif did not in d1 and did in d2:
#                 title = d2[did]["title"]
#                 abstract = d2[did]["abstract"]
#                 tags = d2[did]["tags"]
#             else:
#                 title = d1[did]["title"]
#                 abstract = d1[did]["abstract"]
#                 tags = d1[did]["tags"] + d2[did]["tags"]
#             f.write(f"{title}\n")
#             f.write(f"{abstract}\n")
#             f.write("{}\n\n".format("\n".join(sorted(tags, key=lambda x: int(x.split("\t")[1])))))


# TODO: Add doc
def main():
    parser = ArgumentParser()
    parser.add_argument("--count", help="Count the number of PMC documents in a PubTator file", metavar="FILE")
    parser.add_argument("--split", nargs=2, help="Split the PubTator file into its contained documents",
                        metavar=("FILE", "OUTPUT_DIR"))
    parser.add_argument("--concat", nargs=2,
                        help="Concat PubTator files of directory into a single file (DIR, OUTPUT)")
    parser.add_argument("--merge", nargs=3, metavar=("FILE1", "FILE2", "OUTPUT_FILE"))
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

    if args.merge:
        # merge_pubtator_files(args.merge[0], args.merge[1], args.merge[2])
        raise NotImplementedError


if __name__ == "__main__":
    main()
title_pattern = re.compile(r"^\d+\|t\|")
abstract_pattern = re.compile(r"^\d+\|a\|")
