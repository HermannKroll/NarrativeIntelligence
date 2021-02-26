from collections import namedtuple

import networkx as nx

from narraint.pubtator.document import TaggedEntity

IMPORTANT_KEYWORDS = ["treat", "metabol", "inhibit", "therapy",
                      "adverse", "complications"]
IMPORTANT_PHRASES = ["side effect", "drug toxicity", "drug injury"]


PathIEToken = namedtuple('PathIEToken', ["text", "text_lower", "text_before", "text_after", "index", "charStart",
                                         "charEnd", "pos", "lemma"])

PathIEDependency = namedtuple('PathIEDependency', ["governor_idx", "dependent_idx", "relation"])

PathIEExtraction = namedtuple('PathIEExtraction', ["document_id", "subject_id", "subject_str", "subject_type",
                                                   "predicate", "predicate_lemmatized", "object_id", "object_str",
                                                   "object_type", "sentence"])


def pathie_reconstruct_sentence_sequence_from_tokens(tokens: [PathIEToken]) -> str:
    token_sequence = []
    for t in tokens:
        token_sequence.extend([t.text_before, t.text, t.text_after])
    # remove the last element - it does not belong to the string (after token AFTER the last word)
    # replace doubled spaces
    return ''.join(token_sequence).replace('  ', ' ').strip()


def pathie_reconstruct_text_from_token_indexes(tokens: [PathIEToken], token_indexes: [int]):
    sequence = []
    for t in tokens:
        if t.index in token_indexes:
            sequence.extend([t.text, t.text_after])
    # remove the last element - it does not belong to the string (after token AFTER the last word)
    return ''.join(sequence[:-1])


def pathie_find_tags_in_sentence(tokens: [PathIEToken], doc_tags: [TaggedEntity]):
    tag_token_index_sequences = []
    for tag in doc_tags:
        toks_for_tag = []
        start_token = None
        for tok in tokens:
            if tok.charStart >= tag.start and tok.charEnd <= tag.end:
                toks_for_tag.append(tok.index)
                if not start_token:
                    start_token = tok.text_lower
        # if we found a sequence and the start token matches
        if toks_for_tag and tag.text.lower().startswith(start_token):
            tag_token_index_sequences.append((tag, toks_for_tag))
    return tag_token_index_sequences


def pathie_find_relations_in_sentence(tokens: [PathIEToken], sentence_text_lower: str, important_keywords: [str] = None,
                                      important_phrases: [str] = None):
    idx2word = dict()
    # root is the empty word
    idx2word[0] = ""
    vidx2text_and_lemma = dict()
    for t in tokens:
        # it's a verb
        if t.pos.startswith('V') and t.lemma not in ["have", "be", "do"]:
            vidx2text_and_lemma[t.index] = (t.text, t.lemma)
        else:
            # check if a keyword is mentioned
            if important_keywords:
                for keyword in important_keywords:
                    if keyword in t.text_lower:  # partial included is enough
                        vidx2text_and_lemma[t.index] = (t.text, t.lemma)
    if important_phrases:
        for phrase in important_phrases:
            if phrase in sentence_text_lower:
                phrase_parts = phrase.split(' ')
                phrase_matches = []
                # Reconstruct match based on token indexes
                # Iterate over all tokens and search for matching sequences of subsequent tokens
                for j in range(0, len(tokens) - len(phrase_parts)):
                    phrase_matched = True
                    for i in range(0, len(phrase_parts)):
                        if tokens[j + i].text_lower not in phrase_parts[i]:
                            phrase_matched = False
                            break
                    if phrase_matched:
                        phrase_matches.append([(t.index, t.text, t.lemma) for t in tokens[j:j + len(phrase_parts)]])
                # go through all matches
                for match in phrase_matches:
                    # the whole phrase was matched
                    t_txt = ' '.join([p[1] for p in match])
                    t_lemma = ' '.join([p[2] for p in match])
                    for p in match:
                        # overwrite if a verb was already found for this index
                        vidx2text_and_lemma[p[0]] = (t_txt, t_lemma)
    return vidx2text_and_lemma


def pathie_extract_facts_from_sentence(doc_id: int, doc_tags: [TaggedEntity],
                                       tokens: [PathIEToken],
                                       dependencies: [PathIEDependency],
                                       important_keywords: [str] = None,
                                       important_phrases: [str] = None,
                                       ignore_not_extractions = True,
                                       ignore_may_extraction = True) -> [PathIEExtraction]:
    """
    Extracts fact from a sentence with PathIE
    :param doc_id: document id
    :param doc_tags: a set of document tags (TaggedEntity)
    :param tokens: a list of the sentence's PathIETokens
    :param dependencies: a list of the sentence's dependencies
    :param important_keywords: a set of important lower-cased extraction keywords (single words like treatment)
    :param important_phrases: a set of important lower-cased extraction phrases (whole phrases)
    :return: a list of PathIE extractions
    """
    sentence = pathie_reconstruct_sentence_sequence_from_tokens(tokens).strip()
    sentence_lower = sentence.lower()

    # find all relations in the sentence
    vidx2text_and_lemma = pathie_find_relations_in_sentence(tokens, sentence_lower,
                                                            important_keywords, important_phrases)
    idx2token = {}
    if ignore_not_extractions or ignore_may_extraction:
        idx2token = {t.index : t for t in tokens}

    # no verbs -> no extractions
    if len(vidx2text_and_lemma) == 0:
        return []

    # find entities in sentence
    tag_sequences = pathie_find_tags_in_sentence(tokens, doc_tags)

    # convert the grammatical structure of the sentence into a graph
    dep_graph = nx.Graph()
    node_idxs = set()
    for dep in dependencies:
        governor = int(dep.governor_idx)
        dependent = int(dep.dependent_idx)
        relation = dep.relation

        # delete verbs that are connected with a not
        if ignore_not_extractions:
            if governor in vidx2text_and_lemma and relation == 'advmod' and idx2token[dependent].text_lower in ['not', 'nt']:
                del vidx2text_and_lemma[governor]

        if ignore_may_extraction:
            if governor in vidx2text_and_lemma and relation == 'aux' and idx2token[dependent].text_lower in ['may', 'might']:
                del vidx2text_and_lemma[governor]

        if governor not in node_idxs:
            dep_graph.add_node(governor)
            node_idxs.add(governor)
        if dependent not in node_idxs:
            dep_graph.add_node(dependent)
            node_idxs.add(dependent)
        dep_graph.add_edge(governor, dependent)

    # maybe we have deleted all allowed verbs
    if ignore_not_extractions and len(vidx2text_and_lemma) == 0:
        return []

    extracted_tuples = []
    extracted_index = set()
    # perform the extraction
    # PathIE performs a nested loop search upon the entity start tokens and computes shortest path between them
    # if a verb, keyword or keyphrase appears on the path, a fact will be extracted
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
                                    # only extract one direction
                                    key_e1_e2 = (e1_tag.ent_id, e1_tag.ent_type, v_lemma, e2_tag.ent_id, e2_tag.ent_type)
                                    key_e2_e1 = (e2_tag.ent_id, e2_tag.ent_type, v_lemma, e1_tag.ent_id, e1_tag.ent_type)
                                    if key_e1_e2 in extracted_index or key_e2_e1 in extracted_index:
                                        continue
                                    extracted_index.add(key_e1_e2)
                                    extracted_index.add(key_e2_e1)
                                    extracted_tuples.append(
                                        PathIEExtraction(doc_id,
                                                         e1_tag.ent_id, e1_tag.text, e1_tag.ent_type,
                                                         v_txt, v_lemma,
                                                         e2_tag.ent_id, e2_tag.text, e2_tag.ent_type,
                                                         sentence))
                    except nx.NetworkXNoPath:
                        pass

    return extracted_tuples
