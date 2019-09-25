"""
Tool to create batches from document collcetion in PubTator format.

Input: PubTator file containing documents
Output: PubTator files with specific number of documents
"""
import argparse
import os
from datetime import datetime
from math import ceil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="Input file")
    parser.add_argument("outdir", help="Directory for output")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--size", help="Number of documents per batch (dynamic file number)", type=int)
    group.add_argument("--files", help="Number of batches to create (dynamic batch size)", type=int)
    args = parser.parse_args()

    if not os.path.exists(args.outdir):
        os.mkdir(args.outdir)

    if args.size:
        batch_size = args.size
    else:
        with open(args.infile) as fin:
            lines = [1 for line in fin if line.strip() == ""]
            doc_count = len(lines)
        batch_size = int(ceil(doc_count / float(args.files)))

    start = datetime.now()
    batch_number = 0
    cur_batch_size = 0
    new_file = True
    fout = None
    with open(args.infile) as fin:
        for line in fin:
            if new_file:
                fout = open(os.path.join(args.outdir, "batch{:02d}.txt".format(batch_number)), "w")
                new_file = False
            fout.write(line)
            if line.strip() == "":
                cur_batch_size += 1
            if cur_batch_size >= batch_size:
                batch_number += 1
                cur_batch_size = 0
                new_file = True
                fout.close()

    end = datetime.now()
    print("Done in {}".format(end - start))


if __name__ == "__main__":
    main()
