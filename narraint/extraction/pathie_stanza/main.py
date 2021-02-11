import argparse
import stanza
from datetime import datetime
import logging
import networkx as nx
from spacy.lang.en import English

from narraint.extraction.extraction_utils import  filter_document_sentences_without_tags

from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents
from narraint.pubtator.document import  TaggedEntity

IMPORTANT_KEYWORDS = ["treat", "metabol", "inhibit", "therapy",
                      "adverse", "complications"]
IMPORTANT_PHRASES = ["side effect", "drug toxicity", "drug injury"]


def pathie_stanza_reconstruct_sentence_sequence_from_nlp_output(tokens):
    token_sequence = []
    for t in tokens:
        t_txt = t["text"]
        token_sequence.extend([t_txt, ' '])
    # remove the last element - it does not belong to the string (after token AFTER the last word)
    return ''.join(token_sequence[:-1])


def pathie_stanza_reconstruct_text_from_token_indexes(tokens, token_indexes):
    sequence = []
    for t in tokens:
        if t["id"][0] in token_indexes:
            sequence.extend([t["text"], " "])
    # remove the last element - it does not belong to the string (after token AFTER the last word)
    return ''.join(sequence[:-1])


def pathie_stanza_find_tags_in_sentence(tokens, doc_tags: [TaggedEntity]):
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


def pathie_stanza_find_relations_in_sentence(tokens, sentence_text_lower):
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


def pathie_stanza_convert_sentence_to_triples(doc_id: int, sentence, doc_tags):
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
    verbs, vidx2text_and_lemma = pathie_stanza_find_relations_in_sentence(tokens, sentence_lower)

    # no verbs -> no extractions
    if len(verbs) == 0:
        return []

    # find entities in sentence
    tag_sequences = pathie_stanza_find_tags_in_sentence(tokens, doc_tags)

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


def pathie_stanza_extract_interactions(doc2sentences, doc2tags, amount_files, output):
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
                extracted_tuples.extend(pathie_stanza_convert_sentence_to_triples(doc_id, sent, doc_tags))

            print_progress_with_eta("pathie: processing documents...", idx, amount_files, start_time, print_every_k=1)
            for e_tuple in extracted_tuples:
                line = '\t'.join([str(t) for t in e_tuple])
                if first_line:
                    first_line = False
                    f_out.write(line)
                else:
                    f_out.write('\n' + line)


def run_stanza_pathie(input_file, output):
    """
    Executes PathIE via Stanza
    :param input_file: the PubTator input file (tags must be included)
    :param output: extractions will be written to output
    :return: None
    """
    logging.info('Init spacy nlp...')
    spacy_nlp = English()  # just the language with no model
    sentencizer = spacy_nlp.create_pipe("sentencizer")
    spacy_nlp.add_pipe(sentencizer)

    # Prepare files
    doc_count = count_documents(input_file)
    logging.info('{} documents counted'.format(doc_count))

    doc2sentences, doc2tags = filter_document_sentences_without_tags(doc_count, input_file, spacy_nlp)
    amount_files = len(doc2tags)

    if amount_files == 0:
        print('no files to process - stopping')
    else:
        start = datetime.now()
        # Process output
        pathie_stanza_extract_interactions(doc2sentences, doc2tags, amount_files, output)
        print(" done in {}".format(datetime.now() - start))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="PubTator file / directory of PubTator files - PubTator files must include Tags")
    parser.add_argument("output", help="PathIE output file")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    run_stanza_pathie(args.input, args.output)


if __name__ == "__main__":
    main()
