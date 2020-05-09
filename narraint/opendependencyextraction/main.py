import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from time import sleep
import logging
import networkx as nx

from narraint.graph.labeled import LabeledGraph
from narraint.progress import print_progress_with_eta
from narraint.config import OPENIE_CONFIG
from narraint.pubtator.document import TaggedDocument
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS
from narraint.pubtator.extract import read_pubtator_documents

PATH_EXTRACTION = "PATH"
CORENLP_VERSION = "4.0.0"

NUMBER_FIX_REGEX = re.compile(r"\d+,\d+")
IMPORTANT_KEYWORDS = ["treat", "metabol", "inhibit", "therapy"]


def filter_document_sentences_without_tags_enhanced(doc_size, input_file, corenlp_dir, openie_filelist):
    logging.info('Filtering {} documents (keep only document sentences with tags)'.format(doc_size))
    amount_skipped_files = 0
    openie_files = []
    doc2tags = dict()
    start_time = datetime.now()
    for idx, pubtator_content in enumerate(read_pubtator_documents(input_file)):
        tagged_doc = TaggedDocument(pubtator_content)
        doc_id = tagged_doc.id
        tags = tagged_doc.tags
        tag_terms = set()
        tag_terms_lower = set()
        for t in tags:
            tag_terms.add((t.mesh, '{}'.format(t.text.lower()), t.type))
            tag_terms_lower.add(' {}'.format(t.text.lower()))
        doc2tags[doc_id] = tag_terms

        filtered_content = set()
        for sent in tagged_doc.sentence_by_id.values():
            sent_lower = ' {}'.format(sent.text.lower())
            hits = 0
            for t_str in tag_terms_lower:
                hits += sent_lower.count(t_str)
                if hits >= 2:
                    break
            if hits >= 2:
                filtered_content.add(sent.text)

        #filtered_test = []
        for sent, ent_ids in tagged_doc.entities_by_sentence.items():
            if len(ent_ids) > 1:  # at minimum two tags must be included in this sentence
                filtered_content.add(tagged_doc.sentence_by_id[sent].text)



        #if len(filtered_test) > len(filtered_content):
         #   print('Filtered too many sentences {} (self) vs {} (real tagged)'.format(len(filtered_content),
             #                                                                                   len(filtered_test)))
        # skip empty documents
        if not filtered_content:
            continue
        # write filtered document
        o_file = os.path.join(corenlp_dir, '{}.txt'.format(doc_id))
        openie_files.append(o_file)
        with open(o_file, 'w') as f_out:
            f_out.write('. '.join(filtered_content))

        print_progress_with_eta('filtering documents...', idx, doc_size, start_time, print_every_k=10)

    logging.info('{} files need to be processed. {} files skipped.'.format(len(openie_files), amount_skipped_files))
    with open(openie_filelist, "w") as f:
        f.write("\n".join(openie_files))
    return len(openie_files), doc2tags


def prepare_files_old(input, temp_dir):
    temp_in_dir = os.path.join(temp_dir, "input")
    filelist_fn = os.path.join(temp_dir, "filelist.txt")
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
            doc_id, title, abstract = match.group(1, 2, 3)
            content = f"{title}. {abstract}"
            input_file = os.path.join(temp_in_dir, "{}.txt".format(doc_id))
            input_files.append(input_file)
            with open(input_file, "w") as f:
                f.write(content)

    logging.info('{} files need to be processed. {} files skipped.'.format(amount_files, amount_skipped_files))
    with open(filelist_fn, "w") as f:
        f.write("\n".join(input_files))

    return filelist_fn, amount_files


def get_progress(out_corenlp_dir):
    hits = 0
    for fn in os.listdir(out_corenlp_dir):
        if fn.endswith('.json'):
            hits += 1
    return hits


def run_corenlp(core_nlp_dir, out_corenlp_dir, filelist_fn):
    start = datetime.now()
    with open(filelist_fn) as f:
        num_files = len(f.read().split("\n"))

    run_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh")
    sp_args = ["/bin/bash", "-c", "{} {} {} {}".format(run_script, core_nlp_dir, out_corenlp_dir, filelist_fn)]
    process = subprocess.Popen(sp_args, cwd=core_nlp_dir)
    start_time = datetime.now()
    while process.poll() is None:
        sleep(30)
        print_progress_with_eta('OpenIE running...', get_progress(out_corenlp_dir), num_files, start_time, print_every_k=1)
    sys.stdout.write("\rProgress: {}/{} ... done in {}\n".format(
        get_progress(out_corenlp_dir), num_files, datetime.now() - start,
    ))
    sys.stdout.flush()


def convert_sentence_to_triples(doc_id: int, sentence_json: dict, doc_tags):
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
    for tag_id, tag_str, tag_type in doc_tags:
        tag_stripped = tag_str.strip()
        if tag_str in sentence_lower:
            # find the correct indexes
            if ' ' in tag_stripped:
                ent_token_ids = []
                for t_part in tag_stripped.split(' '):
                    for tok, idx in tok2idx.items():
                        if t_part in tok:
                            ent_token_ids.append(idx)
                entities_in_sentence.append((tag_id, tag_stripped, tag_type, ent_token_ids))
            else:
                for tok, idx in tok2idx.items():
                    if tag_stripped in tok:
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

 #   for t in extracted_tuples:
  #      print('({}, {}, {}) <- {}'.format(t[1], t[2], t[4], t[5]))
    return extracted_tuples


def process_file(doc_id, input_file, doc2tags):
    extracted_tuples = []
    with open(input_file, 'r') as f:
        print('Processing input file: {}'.format(input_file))
        json_fixed_lines = []
        for line in f:
            if NUMBER_FIX_REGEX.findall(line):
                json_fixed_lines.append(line.replace(',', '.', 1))
            else:
                json_fixed_lines.append(line)

        json_data = json.loads(''.join(json_fixed_lines))
        for sent in json_data["sentences"]:
            extracted_tuples.extend(convert_sentence_to_triples(doc_id, sent, doc2tags))
    return extracted_tuples


def process_output(out_corenlp_dir, amount_files, outfile, doc2tags):
    tuples = 0
    start_time = datetime.now()
    with open(outfile, 'wt') as f_out:
        first_line = True
        for idx, filename in enumerate(os.listdir(out_corenlp_dir)):
            if filename.endswith('.json'):
                doc_id = int(filename.split('.')[0])
                extracted_tuples = process_file(doc_id, os.path.join(out_corenlp_dir, filename), doc2tags[doc_id])
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
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="single pubtator file (containing multiple documents) or directory of "
                                      "pubtator files")
    parser.add_argument("output", help="File with OpenIE results")
    parser.add_argument("workdir", help="File with OpenIE results")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    core_nlp_dir = "/home/kroll/tools/stanford-corenlp-4.0.0/stanford-corenlp-4.0.0/"
    temp_dir = args.workdir # '/home/kroll/workingdir/corenlp/temp_simvastatin_cholesterol/' # tempfile.mkdtemp()
    out_corenlp_dir = os.path.join(temp_dir, "output")
    temp_in_dir = os.path.join(temp_dir, "input")
    filelist_fn = os.path.join(temp_dir, "filelist.txt")
    if not os.path.isdir(temp_in_dir):
        os.mkdir(temp_in_dir)
    if not os.path.isdir(out_corenlp_dir):
        os.mkdir(out_corenlp_dir)
    logging.info('Working in: {}'.format(temp_dir))
    # Prepare files
    amount_files, doc2tags = filter_document_sentences_without_tags_enhanced(12000, args.input, temp_in_dir, filelist_fn)
    if amount_files == 0:
        print('no files to process - stopping')
    else:
        run_corenlp(core_nlp_dir, out_corenlp_dir, filelist_fn)
        print("Processing output ...", end="")
        start = datetime.now()
        # Process output
      #  process_output(out_corenlp_dir, amount_files, args.output, doc2tags)
        print(" done in {}".format(datetime.now() - start))


if __name__ == "__main__":
    main()
