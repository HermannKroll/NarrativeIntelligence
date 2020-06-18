import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from time import sleep
import logging

from narraint.progress import print_progress_with_eta
from narraint.config import OPENIE_CONFIG
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS
from narraint.pubtator.extract import read_pubtator_documents


def prepare_files(input):
    """
    Converts a PubTator file into plain texts files which can be processed by OpenIE
    Easily speaking, writes title and abstract of a PubTator file to a plain text file
    Creates a new temporary directory as a workign dir
    :param input: a PubTator file / a directory of PubTator files
    :return: a filelist for OpenIE, the location where the OpenIE output should be stored, the amount of files
    """
    temp_dir = tempfile.mkdtemp()
    temp_in_dir = os.path.join(temp_dir, "input")
    filelist_fn = os.path.join(temp_dir, "filelist.txt")
    out_fn = os.path.join(temp_dir, "output.txt")
    os.mkdir(temp_in_dir)
    input_files = []

    amount_skipped_files = 0
    amount_files = 0
    logging.info('counting files to process....')
    for document_content in read_pubtator_documents(input):
        match = CONTENT_ID_TIT_ABS.match(document_content)
        if not match:
            amount_skipped_files += 1
        else:
            amount_files += 1
            pmid, title, abstract = match.group(1, 2, 3)
            content = f"{title}. {abstract}"
            input_file = os.path.join(temp_in_dir, "{}.txt".format(pmid))
            input_files.append(input_file)
            with open(input_file, "w") as f:
                f.write(content)

    logging.info('{} files need to be processed. {} files skipped.'.format(amount_files, amount_skipped_files))
    with open(filelist_fn, "w") as f:
        f.write("\n".join(input_files))
    return filelist_fn, out_fn, amount_files


def get_progress(out_fn):
    """
    Get the progress of how many files have already been processed by OpenIE
    :param out_fn: The output file of OpenIE
    :return: the amount of processed files
    """
    if not os.path.exists(out_fn):
        return 0
    else:
        with open(out_fn) as f:
            doc_names = []
            for line in f:
                d = line.split('\t', 1)[0]
                doc_names.append(d)
            return len(set(doc_names))


def run_openie(core_nlp_dir, out_fn, filelist_fn):
    """
    Invokes the startup of OpenIE
    :param core_nlp_dir: Directory of Stanford OpenIE toolkit (CoreNLP(
    :param out_fn: OpenIE output file
    :param filelist_fn: the filelist which files should be processed
    :return: None
    """
    start = datetime.now()
    with open(filelist_fn) as f:
        num_files = len(f.read().split("\n"))

    run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh")
    sp_args = ["/bin/bash", "-c", "{} {} {} {}".format(run_script, core_nlp_dir, out_fn, filelist_fn)]
    process = subprocess.Popen(sp_args, cwd=core_nlp_dir)
    start_time = datetime.now()
    while process.poll() is None:
        sleep(30)
        print_progress_with_eta('OpenIE running...', get_progress(out_fn), num_files, start_time, print_every_k=1)
    sys.stdout.write("\rProgress: {}/{} ... done in {}\n".format(
        get_progress(out_fn), num_files, datetime.now() - start,
    ))
    sys.stdout.flush()


def match_pred_tokens(pred, pos_tags, pred_start, pred_end, sent):
    """
    matches the predicate tokens in the sentence and extracts the correct pos tags
    :param pred: predicate string
    :param pos_tags: list of pos tags of the whole sentence
    :param pred_start: start position of the predicate in the sentence
    :param pred_end: end position of the predicate in the sentence
    :param sent: the whole sentence
    :return: a list of pos tags if matched is successful, else None
    """
    # the format seems to be strange some times
    if pred_end < pred_start:
        temp = pred_start
        pred_start = pred_end
        pred_end = temp

    if pred_start == pred_end:
        return pos_tags[pred_start]
    else:
        tokens_sent = sent.lower().split(' ')[pred_start:pred_end]
        tokens_pred = pred.split(' ')
        pred_pos_tags_list = []

        # try to match all pred tokens in the sentence tokens
        for p_tok in tokens_pred:
            for idx, s_tok in enumerate(tokens_sent):
                if p_tok == s_tok:
                    pred_pos_tags_list.append(pos_tags[idx])

        if len(pred_pos_tags_list) != len(tokens_pred):
            return None
        return ' '.join(pred_pos_tags_list)


def process_output(openie_out, outfile):
    tuples = 0
    with open(openie_out, 'r') as f_out, open(outfile, 'w') as f_conv:
        for idx, line in enumerate(f_out):
            tuples += 1
            components = line.strip().split("\t")
            # e.g. first line looks like /tmp/tmpwi57otrk/input/1065332.txt (so pmid is between last / and .)
            pmid = components[0].split("/")[-1].split('.')[0]
            subj = components[2].lower()
            pred = components[3].lower()
            obj = components[4].lower()
            conf = components[11].replace(',', '.')
            sent = components[-5]
            pred_lemma = components[-2]

            res = [pmid, subj, pred, pred_lemma, obj, conf, sent]
            if idx == 0:
                f_conv.write('\t'.join(t for t in res))
            else:
                f_conv.write('\n' + '\t'.join(t for t in res))

    logging.info('{} lines written'.format(tuples))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="single pubtator file (containing multiple documents) or directory of "
                                      "pubtator files")
    parser.add_argument("output", help="File with OpenIE results")
    parser.add_argument("--conf", default=OPENIE_CONFIG)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    # Read config
    with open(args.conf) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]

    # Prepare files
    filelist_fn, out_fn, amount_files = prepare_files(args.input)

    if amount_files == 0:
        print('no files to process - stopping')
    else:
        run_openie(core_nlp_dir, out_fn, filelist_fn)
        print("Processing output ...", end="")
        start = datetime.now()
        # Process output
        process_output(out_fn, args.output)
        print(" done in {}".format(datetime.now() - start))


if __name__ == "__main__":
    main()
