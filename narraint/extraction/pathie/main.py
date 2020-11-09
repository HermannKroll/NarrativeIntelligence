import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from time import sleep
import logging
import networkx as nx
from spacy.lang.en import English

from narraint.config import PATHIE_CONFIG
from narraint.extraction.extraction_utils import filter_and_write_documents_to_tempdir

from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents
from narraint.pubtator.document import TaggedDocument
from narraint.pubtator.extract import read_pubtator_documents

NUMBER_FIX_REGEX = re.compile(r"\d+,\d+")
IMPORTANT_KEYWORDS = ["treat", "metabol", "inhibit", "therapy",
                      "side effect", "adverse", "complications",
                      "drug toxicity", "drug injury"]


def get_progress(out_corenlp_dir: str) -> int:
    """
    Get the current progress of the NLP tool
    :param out_corenlp_dir: reads the output dir and checks how many .json files have been created already
    :return: length of processed documents
    """
    hits = 0
    for fn in os.listdir(out_corenlp_dir):
        if fn.endswith('.json'):
            hits += 1
    return hits


def pathie_run_corenlp(core_nlp_dir: str, out_corenlp_dir: str, filelist_fn: str):
    """
    Invokes the Stanford CoreNLP tool to process files
    :param core_nlp_dir: CoreNLP tool directory
    :param out_corenlp_dir: the output directory
    :param filelist_fn: the path of the filelist which files should be processed
    :return: None
    """
    start = datetime.now()
    with open(filelist_fn) as f:
        num_files = len(f.read().split("\n"))

    run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh")
    sp_args = ["/bin/bash", "-c", "{} {} {} {}".format(run_script, core_nlp_dir, out_corenlp_dir, filelist_fn)]
    process = subprocess.Popen(sp_args, cwd=core_nlp_dir)
    start_time = datetime.now()
    while process.poll() is None:
        sleep(30)
        print_progress_with_eta('CoreNLP running...', get_progress(out_corenlp_dir), num_files, start_time,
                                print_every_k=1)
    sys.stdout.write("\rProgress: {}/{} ... done in {}\n".format(
        get_progress(out_corenlp_dir), num_files, datetime.now() - start,
    ))
    sys.stdout.flush()


def convert_sentence_to_triples(doc_id: int, sentence_json: dict, doc_tags):
    """
    PathIE extraction procedure
    1. Reads CoreNLP JSON output
    2. Converts EnhancedDependenciesPlusPlus into a graph
    3. Performs a Path search on this graph between the entities
    4. if a predicate / keyword is included on the path, a fact is extracted
    :param doc_id: the document id
    :param sentence_json: json sentence parse
    :param doc_tags: dict mapping doc ids to tags
    :return:
    """
    enhan_deps = sentence_json["enhancedPlusPlusDependencies"]
    tokens = sentence_json["tokens"]
    sentence_parts = []
    idx2word = dict()
    # root is the empty word
    idx2word[0] = ""
    tok2idx = dict()
    verbs = []
    vidx2text_and_lemma = dict()
    for t in tokens:
        t_id = t["index"]
        t_txt = t["originalText"]
        t_pos = t["pos"]
        t_lemma = t["lemma"]
        idx2word[t_id] = t_txt
        sentence_parts.append(t_txt)
        tok2idx[t_txt.lower()] = t_id
        # its a verb
        if t_pos.startswith('V') and t_lemma not in ["have", "be"]:
            vidx2text_and_lemma[t_id] = (t_txt, t_lemma)
            verbs.append((t_id, t_txt, t_lemma))
        else:
            t_lower = t_txt.lower().strip()
            for keyword in IMPORTANT_KEYWORDS:
                if keyword in t_lower:
                    vidx2text_and_lemma[t_id] = (t_txt, t_lemma)
                    verbs.append((t_id, t_txt, t_lemma))

    # no verbs -> no extractions
    if len(verbs) == 0:
        return []

    sentence = ' '.join(sentence_parts).strip()
    sentence_lower = sentence.lower()
    entities_in_sentence = []
    for tag_id, tag_str_lower, tag_type in doc_tags:
        tag_stripped = tag_str_lower.strip()
        if tag_str_lower in sentence_lower:
            # find the correct indexes
            if ' ' in tag_stripped:
                ent_token_ids = []
                for t_part in tag_stripped.split(' '):
                    for tok, idx in tok2idx.items():
                        if tok == t_part:
                            ent_token_ids.append(idx)
                entities_in_sentence.append((tag_id, tag_stripped, tag_type, ent_token_ids))
            else:
                for tok, idx in tok2idx.items():
                    if tok == tag_stripped:
                        entities_in_sentence.append((tag_id, tag_stripped, tag_type, [idx]))

    dep_graph = nx.Graph()
    node_idxs = set()
    for dep_json in enhan_deps:
        dep = dep_json["dep"]
        governor = int(dep_json["governor"])
        governor_gloss = dep_json["governorGloss"]
        dependent = int(dep_json["dependent"])
        dependent_gloss = dep_json["dependentGloss"]

        if governor not in node_idxs:
            dep_graph.add_node(governor)
            node_idxs.add(governor)
        if dependent not in node_idxs:
            dep_graph.add_node(dependent)
            node_idxs.add(dependent)
        dep_graph.add_edge(governor, dependent)

    extracted_tuples = []
    extracted_index = set()
    for e1_id, e1_str, e1_type, e1_token_ids in entities_in_sentence:
        for e1_tok_id in e1_token_ids:
            for e2_id, e2_str, e2_type, e2_token_ids in entities_in_sentence:
                if e1_str == e2_str:
                    continue
                for e2_tok_id in e2_token_ids:
                    try:
                        for path in nx.all_shortest_paths(dep_graph, source=e1_tok_id, target=e2_tok_id):
                            for n_idx in path:
                                if n_idx in vidx2text_and_lemma:
                                    # this is a valid path
                                    v_txt, v_lemma = vidx2text_and_lemma[n_idx]
                                    key = (e1_id, e1_type, v_lemma, e2_id, e2_type)
                                    if key in extracted_index:
                                        continue
                                    extracted_index.add(key)
                                    extracted_tuples.append((doc_id, e1_id, e1_str, e1_type, v_txt, v_lemma,
                                                             e2_id, e2_str, e2_type, sentence))
                    except nx.NetworkXNoPath:
                        pass

    return extracted_tuples


def process_json_file(doc_id, input_file, doc_tags):
    """
    Extracts facts out of a JSON file
    :param doc_id: document id
    :param input_file: JSON input file as a filename
    :param doc_tags: set of tags in the corresponding document
    :return: a list of extracted tuples
    """
    extracted_tuples = []
    with open(input_file, 'r') as f:
        json_fixed_lines = []
        for line in f:
            if NUMBER_FIX_REGEX.findall(line):
                json_fixed_lines.append(line.replace(',', '.', 1))
            else:
                json_fixed_lines.append(line)
        json_data = json.loads(''.join(json_fixed_lines))
        for sent in json_data["sentences"]:
            extracted_tuples.extend(convert_sentence_to_triples(doc_id, sent, doc_tags))
    return extracted_tuples


def pathie_process_corenlp_output(out_corenlp_dir, amount_files, outfile, doc2tags):
    """
    Processes the CoreNLP output directory: iterates over all files and calls the process_json_file function
    :param out_corenlp_dir: CoreNLP output directory (dir of .json files)
    :param amount_files: amount of files
    :param outfile: filename where all extractions will be stored
    :param doc2tags: dict mapping doc ids to tags
    :return: None
    """
    tuples = 0
    start_time = datetime.now()
    with open(outfile, 'wt') as f_out:
        first_line = True
        for idx, filename in enumerate(os.listdir(out_corenlp_dir)):
            if filename.endswith('.json'):
                doc_id = int(filename.split('.')[0])
                extracted_tuples = process_json_file(doc_id, os.path.join(out_corenlp_dir, filename), doc2tags[doc_id])
                for e_tuple in extracted_tuples:
                    line = '\t'.join([str(t) for t in e_tuple])
                    if first_line:
                        first_line = False
                        f_out.write(line)
                    else:
                        f_out.write('\n' + line)
            print_progress_with_eta("extracting triples", idx, amount_files, start_time, print_every_k=1)
    logging.info('{} lines written'.format(tuples))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="PubTator file / directory of PubTator files - PubTator files must include Tags")
    parser.add_argument("output", help="PathIE output file")
    parser.add_argument("--workdir", help="working directory")
    parser.add_argument("--conf", default=PATHIE_CONFIG)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    # Read config
    with open(args.conf) as f:
        conf = json.load(f)
        core_nlp_dir = conf["corenlp"]

    if args.workdir:
        temp_dir = args.workdir
    else:
        temp_dir = tempfile.mkdtemp()
    out_corenlp_dir = os.path.join(temp_dir, "output")
    temp_in_dir = os.path.join(temp_dir, "input")
    filelist_fn = os.path.join(temp_dir, "filelist.txt")
    if not os.path.isdir(temp_in_dir):
        os.mkdir(temp_in_dir)
    if not os.path.isdir(out_corenlp_dir):
        os.mkdir(out_corenlp_dir)
    logging.info('Working in: {}'.format(temp_dir))

    logging.info('Init spacy nlp...')
    spacy_nlp = English()  # just the language with no model
    sentencizer = spacy_nlp.create_pipe("sentencizer")
    spacy_nlp.add_pipe(sentencizer)

    # Prepare files
    doc_count = count_documents(args.input)
    logging.info('{} documents counted'.format(doc_count))
    amount_files, doc2tags = filter_and_write_documents_to_tempdir(doc_count, args.input, temp_in_dir, filelist_fn, spacy_nlp)
    if amount_files == 0:
        print('no files to process - stopping')
    else:
        pathie_run_corenlp(core_nlp_dir, out_corenlp_dir, filelist_fn)
        print("Processing output ...", end="")
        start = datetime.now()
        # Process output
        pathie_process_corenlp_output(out_corenlp_dir, amount_files, args.output, doc2tags)
        print(" done in {}".format(datetime.now() - start))


if __name__ == "__main__":
    main()
