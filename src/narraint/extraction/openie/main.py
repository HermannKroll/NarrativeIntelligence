import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from time import sleep
import logging

from narrant.progress import print_progress_with_eta
from narraint.config import NLP_CONFIG
from narrant.pubtator.document import TaggedDocument
from narrant.pubtator.regex import CONTENT_ID_TIT_ABS
from narrant.pubtator.extract import read_pubtator_documents


def openie_prepare_files(input):
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
        doc = TaggedDocument(pubtator_content=document_content)
        if not doc or not doc.title or not doc.abstract:
            amount_skipped_files += 1
        else:
            amount_files += 1
            content = f"{doc.title}. {doc.abstract}"
            input_file = os.path.join(temp_in_dir, "{}.txt".format(doc.id))
            input_files.append(input_file)
            with open(input_file, "w") as f:
                f.write(content)

    logging.info('{} files need to be processed. {} files skipped.'.format(amount_files, amount_skipped_files))
    with open(filelist_fn, "w") as f:
        f.write("\n".join(input_files))
    return filelist_fn, out_fn, amount_files


def openie_get_progress(out_fn):
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


def openie_run(core_nlp_dir: str, out_fn: str, filelist_fn: str):
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
    process = subprocess.Popen(sp_args, cwd=core_nlp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start_time = datetime.now()
    while process.poll() is None:
        sleep(30)
        print_progress_with_eta('OpenIE running...', openie_get_progress(out_fn), num_files, start_time, print_every_k=1)
    sys.stdout.write("\rProgress: {}/{} ... done in {}\n".format(
        openie_get_progress(out_fn), num_files, datetime.now() - start,
    ))
    sys.stdout.flush()


def openie_match_pred_tokens(pred, pos_tags, pred_start, pred_end, sent):
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


def openie_process_output(openie_out: str, outfile: str):
    """
    Transforms the CoreNLP OpenIE Output format to an internal format
    :param openie_out: the OpenIE output file
    :param outfile: the path to the transformed output file
    :return: None
    """
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


def run_corenlp_openie(input_file, output, config=NLP_CONFIG):
    """
    Executes the Stanford CoreNLP OpenIE extraction
    :param input_file: pubtator input file
    :param output: file to write the extractions to
    :param config: NLP configuration
    :return: None
    """
    # Read config
    with open(config) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]

    # Prepare files
    filelist_fn, out_fn, amount_files = openie_prepare_files(input_file)

    if amount_files == 0:
        print('no files to process - stopping')
    else:
        openie_run(core_nlp_dir, out_fn, filelist_fn)
        print("Processing output ...", end="")
        start = datetime.now()
        # Process output
        openie_process_output(out_fn, output)
        print(" done in {}".format(datetime.now() - start))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to input document/documents")
    parser.add_argument("output", help="OpenIE filtered output results")
    parser.add_argument("--config", default=NLP_CONFIG)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    run_corenlp_openie(args.input, args.output, args.config)


if __name__ == "__main__":
    main()
