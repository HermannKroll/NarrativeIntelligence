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
from narraint.extraction.extraction_utils import filter_and_write_documents_to_tempdir, \
    filter_document_sentences_without_tags

from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents
from narraint.pubtator.document import TaggedDocument, TaggedEntity
from narraint.pubtator.extract import read_pubtator_documents

NUMBER_FIX_REGEX = re.compile(r"\d+,\d+")
IMPORTANT_KEYWORDS = ["treat", "metabol", "inhibit", "therapy",
                      "adverse", "complications"]
IMPORTANT_PHRASES = ["side effect", "drug toxicity", "drug injury"]


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
        sleep(10)
        print_progress_with_eta('CoreNLP running...', get_progress(out_corenlp_dir), num_files, start_time,
                                print_every_k=1)
    sys.stdout.write("\rProgress: {}/{} ... done in {}\n".format(
        get_progress(out_corenlp_dir), num_files, datetime.now() - start,
    ))
    sys.stdout.flush()


def pathie_reconstruct_sentence_sequence_from_nlp_output(tokens):
    token_sequence = []
    for t in tokens:
        t_txt = t["text"]
        token_sequence.extend([t_txt, ' '])
    # remove the last element - it does not belong to the string (after token AFTER the last word)
    return ''.join(token_sequence[:-1])


def pathie_reconstruct_text_from_token_indexes(tokens, token_indexes):
    sequence = []
    for t in tokens:
        if t["id"][0] in token_indexes:
            sequence.extend([t["text"], " "])
    # remove the last element - it does not belong to the string (after token AFTER the last word)
    return ''.join(sequence[:-1])


def pathie_find_tags_in_sentence(tokens, doc_tags: [TaggedEntity]):
    tag_token_index_sequences = []
    for tag in doc_tags:
        toks_for_tag = []
        start_token = None
        for tok in tokens:
            if tok.start_char >= tag.start and tok.end_char <= tag.end:
                toks_for_tag.append(tok.id[0])
                if not start_token:
                    start_token = tok.text.lower()
        # if we found a sequence and the start token matches
        if toks_for_tag and tag.text.lower().startswith(start_token):
            tag_token_index_sequences.append((tag, toks_for_tag))
    return tag_token_index_sequences


def pathie_find_relations_in_sentence(tokens, sentence_text_lower):
    idx2word = dict()
    # root is the empty word
    idx2word[0] = ""
    verbs = set()
    vidx2text_and_lemma = dict()

    for t in tokens:
        t_id = t.id[0]
        t_txt = t.text
        for w in t.words:
            t_pos = w.pos
            t_lemma = w.lemma
            # it's a verb
            if t_pos.startswith('V') and t_lemma not in ["have", "be"]:
                vidx2text_and_lemma[t_id] = (t_txt, t_lemma)
                verbs.add((t_id, t_txt, t_lemma))
            else:
            # check if a keyword is mentioned
                t_lower = t_txt.lower().strip()
                for keyword in IMPORTANT_KEYWORDS:
                    if keyword in t_lower: # partial included is enough
                        vidx2text_and_lemma[t_id] = (t_txt, t_lemma)
                        verbs.add((t_id, t_txt, t_lemma))

    for keyphrase in IMPORTANT_PHRASES:
        if keyphrase in sentence_text_lower:
            keyphrase_parts = keyphrase.split(' ')
            parts_found = []
            for part in keyphrase_parts:
                for t in tokens:
                    t_id = t.id[0]
                    t_txt = t.text
                    if t.text.lower() in part:
                        t_lemma = ' '.join([w.lemma for w in t.words])
                        parts_found.append((t_id, t_txt, t_lemma))
            if len(parts_found) == len(keyphrase_parts):
                # the whole phrase was matched
                t_txt = ' '.join([p[1] for p in parts_found])
                t_lemma = ' '.join([p[2] for p in parts_found])
                for p in parts_found:
                    t_id = p[0]
                    vidx2text_and_lemma[t_id] = (t_txt, t_lemma)
                    verbs.add((t_id, t_txt, t_lemma))
    return verbs, vidx2text_and_lemma


def convert_sentence_to_triples(doc_id: int, sentence, doc_tags):
    """
    PathIE extraction procedure
    1. Reads CoreNLP JSON output
    2. Converts EnhancedDependenciesPlusPlus into a graph
    3. Performs a Path search on this graph between the entities
    4. if a predicate / keyword is included on the path, a fact is extracted
    :param doc_id: the document id
    :param sentence: sentence object
    :param doc_tags: dict mapping doc ids to tags
    :return:
    """
    enhan_deps = sentence.dependencies
    tokens = sentence.tokens
    words = sentence.words
    sentence = sentence.text #pathie_reconstruct_sentence_sequence_from_nlp_output(tokens).strip()
    sentence_lower = sentence.lower()

    # find all relations in the sentence
    verbs, vidx2text_and_lemma = pathie_find_relations_in_sentence(tokens, sentence_lower)

    # no verbs -> no extractions
    if len(verbs) == 0:
        return []

    # find entities in sentence
    tag_sequences = pathie_find_tags_in_sentence(tokens, doc_tags)

    dep_graph = nx.Graph()
    node_idxs = set()
    for dependency in enhan_deps:
        w1, relation, w2 = dependency
        governor = w1.id
        dependent = w2.id
        if governor not in node_idxs:
            dep_graph.add_node(governor)
            node_idxs.add(governor)
        if dependent not in node_idxs:
            dep_graph.add_node(dependent)
            node_idxs.add(dependent)
        dep_graph.add_edge(governor, dependent)

    extracted_tuples = []
    extracted_index = set()
    for e1_idx, (e1_tag, e1_token_ids) in enumerate(tag_sequences):
        for e1_tok_id in e1_token_ids:
            for e2_idx, (e2_tag, e2_token_ids) in enumerate(tag_sequences):
                # do not extract relations between the same entity
                if e1_idx == e2_idx:
                    continue
                for e2_tok_id in e2_token_ids:
                    try:
                        for path in nx.all_shortest_paths(dep_graph, source=e1_tok_id, target=e2_tok_id):
                            for n_idx in path:
                                # does this path lead over a relation
                                if n_idx in vidx2text_and_lemma:
                                    # this is a valid path
                                    v_txt, v_lemma = vidx2text_and_lemma[n_idx]
                                    key = (e1_tag.ent_id, e1_tag.ent_type, v_lemma, e2_tag.ent_id, e2_tag.ent_type)
                                    if key in extracted_index:
                                        continue
                                    extracted_index.add(key)
                                    extracted_tuples.append((doc_id, e1_tag.ent_id, e1_tag.text, e1_tag.ent_type, v_txt,
                                                             v_lemma,
                                                             e2_tag.ent_id, e2_tag.text, e2_tag.ent_type, sentence))
                    except nx.NetworkXNoPath:
                        pass

    return extracted_tuples

import stanza

def pathie_extract_interactions(doc2sentences, doc2tags, amount_files, output):
    start_time = datetime.now()
    logging.info('Initializing Stanza Pipeline...')
    nlp = stanza.Pipeline(lang='en', processors='tokenize,mwt,pos,lemma,depparse', use_gpu=True)

    first_line = True
    with open(output, 'wt') as f_out:
        for idx, (doc_id, sentences) in enumerate(doc2sentences.items()):
            doc_tags = doc2tags[doc_id]
            doc_content = ''.join(sentences)
            processed_doc = nlp(doc_content)
            extracted_tuples = []
            for sent in processed_doc.sentences:
                extracted_tuples.extend(convert_sentence_to_triples(doc_id, sent, doc_tags))

            print_progress_with_eta("pathie: processing documents...", idx, amount_files, start_time, print_every_k=1)
            for e_tuple in extracted_tuples:
                line = '\t'.join([str(t) for t in e_tuple])
                if first_line:
                    first_line = False
                    f_out.write(line)
                else:
                    f_out.write('\n' + line)


def load_and_fix_json_nlp_data(json_path):
    """
    Loads and fixes a txt CoreNLP text json file
    :param json_path: path to json file
    :return: json object
    """
    with open(json_path, 'r') as f:
        json_fixed_lines = []
        for line in f:
            if NUMBER_FIX_REGEX.findall(line):
                json_fixed_lines.append(line.replace(',', '.', 1))
            else:
                json_fixed_lines.append(line)
        return json.loads(''.join(json_fixed_lines))


def process_json_file(doc_id, input_file, doc_tags):
    """
    Extracts facts out of a JSON file
    :param doc_id: document id
    :param input_file: JSON input file as a filename
    :param doc_tags: set of tags in the corresponding document
    :return: a list of extracted tuples
    """
    extracted_tuples = []
    json_data = load_and_fix_json_nlp_data(input_file)
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
                tuples += len(extracted_tuples)
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

    doc2sentences, doc2tags = filter_document_sentences_without_tags(doc_count, args.input, spacy_nlp)
    amount_files = len(doc2sentences)
    #amount_files, doc2tags = filter_and_write_documents_to_tempdir(doc_count, args.input, temp_in_dir, filelist_fn,
    #                                                               spacy_nlp)
    if amount_files == 0:
        print('no files to process - stopping')
    else:
        #pathie_run_corenlp(core_nlp_dir, out_corenlp_dir, filelist_fn)
        #print("Processing output ...", end="")
        start = datetime.now()
        # Process output
        pathie_extract_interactions(doc2sentences, doc2tags, amount_files, args.output)
        #pathie_process_corenlp_output(out_corenlp_dir, amount_files, args.output, doc2tags)
        print(" done in {}".format(datetime.now() - start))


if __name__ == "__main__":
    main()