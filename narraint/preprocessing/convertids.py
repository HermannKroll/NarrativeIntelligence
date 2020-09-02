import argparse
import logging
import sys
import os
import re

from datetime import datetime, timedelta
from itertools import islice

from narraint.preprocessing.config import Config
from narraint.pubtator.count import count_documents
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import DOCUMENT_ID, TAG_LINE_NORMAL
from narraint.progress import print_progress_with_eta


def load_pmcids_to_pmid_index(index_file):
    """
    load a tsv file containing a mapping from pmcids to pmids
    :param index_file: tsv file of the mapping
    :return: a dict as mapping
    """
    pmcid2pmid = {}
    with open(index_file, 'r') as f:
        for line in islice(f, 1, None):
            split = line.split('\t')
            try:
                pmcid = int(split[0])
                pmid = int(split[1][:-1]) # skip \n
                pmcid2pmid[pmcid] = pmid
            except ValueError:
                pass
                # print('Support only integers as ids: {}'.format(split))
    return pmcid2pmid


def convert_pmcids_files_to_pmid_files(input, output, pmcid2pmid):
    """
    converts the ids of a directory of pubtator files / single pubtator
    from pmcid to pmid replacing all occurrences of the id in the document
    :param input: directory of pubtator files / single pubtator file
    :param output: directory (all files will be written in this dir) / single file (all files will be written into this file)
    :param pmcid2pmid: the mapping from pmcids to pmids
    :return: None
    """
    sys.stdout.write("counting documents ...")
    sys.stdout.flush()
    n_docs = count_documents(input)
    sys.stdout.write("\rcounting documents ... found {}\n".format(n_docs))
    sys.stdout.flush()

    is_open = False
    output_f = None

    skipped = 0
    start_time = datetime.now()
    eta = "N/A"
    for idx, pubtator_content in enumerate(read_pubtator_documents(input)):
        # skip empty documents
        if pubtator_content == "":
            continue
        if re.match(DOCUMENT_ID, pubtator_content):
            pmcid = pubtator_content.split('|')[0]
        elif re.match(TAG_LINE_NORMAL, pubtator_content):
            pmcid = pubtator_content.split('\t')[0]
        else:
            raise IOError('unknown input format:\n{}'.format(pubtator_content))

        if pmcid not in pmcid2pmid:
            skipped += 1
            continue

        new_id = pmcid2pmid[pmcid]
        pubtator_content_new = pubtator_content.replace(str(pmcid), str(new_id))

        # is output a directory or file
        if output.endswith('/'):
            # dir
            filename = os.path.join(output, '{}.txt'.format(new_id))
            with open(filename, 'w') as f:
                f.write(pubtator_content_new)
        else:
            # file
            if not is_open:
                output_f = open(output, 'w')
                is_open = True
            output_f.write(pubtator_content_new)

        print_progress_with_eta("converting documents", idx, n_docs, start_time)

    sys.stdout.write("\rconverting documents ... done in {}".format(datetime.now() - start_time))
    # close output file
    if is_open:
        output_f.close()

    sys.stdout.write("\nskipped {} documents due to missing id translation".format(skipped))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    # Create configuration wrapper
    conf = Config(args.config)

    print('loading pmcid to pmid translation file...')
    pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)

    if args.log:
        logging.basicConfig()

    convert_pmcids_files_to_pmid_files(args.input, args.output, pmcid2pmid)


if __name__ == "__main__":
    main()
