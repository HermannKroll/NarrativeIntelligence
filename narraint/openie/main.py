import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from time import sleep

from narraint.config import OPENIE_CONFIG

PUBTATOR_REGEX = re.compile(r"(\d+)\|t\|(.*?)\n\d+\|a\|(.*?)\n")


def prepare_files(input_dir):
    temp_dir = tempfile.mkdtemp()
    temp_in_dir = os.path.join(temp_dir, "input")
    filelist_fn = os.path.join(temp_dir, "filelist.txt")
    out_fn = os.path.join(temp_dir, "output.txt")
    os.mkdir(temp_in_dir)
    input_files = []

    amount_skipped_files = 0
    amount_files = 0
    for fn in os.listdir(input_dir):
        with open(os.path.join(input_dir, fn)) as f:
            document = f.read().strip()
        match = PUBTATOR_REGEX.match(document)
        if not match:
            amount_skipped_files += 1
            print(f"WARNING: Ignoring {fn} (no pubtator format found)")
        else:
            amount_files += 1
            pmid, title, abstract = match.group(1, 2, 3)
            content = f"{title}. {abstract}"
            input_file = os.path.join(temp_in_dir, "{}.txt".format(pmid))
            input_files.append(input_file)
            with open(input_file, "w") as f:
                f.write(content)

    print('{} files need to be processed. {} files skipped.'.format(amount_files, amount_skipped_files))
    with open(filelist_fn, "w") as f:
        f.write("\n".join(input_files))

    return filelist_fn, out_fn, amount_files


def run_process(core_nlp_dir, out_fn, filelist_fn):
    run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh")
    sp_args = ["/bin/bash", "-c", "{} {} {} {}".format(run_script, core_nlp_dir, out_fn, filelist_fn)]
    process = subprocess.Popen(sp_args, cwd=core_nlp_dir)
    while process.poll() is None:
        print("Still processing ...")
        sleep(20)


def process_output(openie_out, outfile):
    lines = []
    with open(openie_out) as f:
        for line in f:
            components = line.strip().split("\t")
            pmid = components[0].split("/")[-1][:-4]
            sent = components[-5]
            subj = components[-3]
            pred = components[-2]
            obj = components[-1]
            lines.append((pmid, subj, pred, obj, sent))

    with open(outfile, "w") as f:
        f.write("\n".join("\t".join(t) for t in lines))


def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--conf", default=OPENIE_CONFIG)
    args = parser.parse_args()

    # Read config
    with open(args.conf) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]

    # Prepare files
    filelist_fn, out_fn, amount_files = prepare_files(args.input)

    if amount_files == 0:
        print('no files to process - stopping')
        return
    # Start
    start = datetime.now()
    run_process(core_nlp_dir, out_fn, filelist_fn)
    print("Finished in {}".format(datetime.now() - start))

    # Process output
    process_output(out_fn, args.output)


if __name__ == "__main__":
    main()
