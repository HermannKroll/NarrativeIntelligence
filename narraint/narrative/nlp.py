"""
Task: Extract subject-predicate, predicate-object, s-p-o pairs from documents

https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html

----------------------------------------
INPUT: Text file in PubTator format with tagged documents
OUTPUT: subject-predicate, predicate-object, subject-predicate-object with MESH terms and predicates

SENT_BY_DOC = {}
SENT_BY_ID = {}
PAIRS_BY_SENT = {}

FOR EACH document d
    Split d into sentences S(d)
    Parse dependencies for each S(d)
    Assign an ID to each sent in S(d): id: S(d) -> N

    SENT_BY_ID[id(sent)] = sent
    SENT_BY_DOC[d] = id(S(d))

    Collect pairs P(sent) = (s,p), (p,o), (s,p,o) from each sent in S(d)
        Use only pairs if s and o are in MESH
        Use only lemmatized predicates p
        TODO: Find synonyms of predicates p
    PAIRS_BY_SENT[id(sent)] = P(sent)

// Create index
Store all predicates in a file: predicates.txt
Store all pairs in three files: sp.txt, po.txt, spo.txt
    Format: DOC_ID PREDICATE MESH [MESH]
DONE.
----------------------------------------

For the set of sentences, build the NLP dependency tree.
Use lemmatization to build a set of synonyms for the predicates (e.g., is metabolized, metabolizes, ...)
"""
import argparse
import os
from datetime import datetime

import stanfordnlp

from narraint.config import NLP_DATA
from narraint.pubtator.document import TaggedDocument

DEP_REL_OBJ = ["comp", "acomp", "ccomp", "xcomp", "obj", "dobj", "iobj", "pobj", "obl"]
DEP_REL_SUBJ = ["nsubj", "subj", "csubj", "nsubj:pass"]
CORPUS_DOCUMENT = "corpus.txt"
DEFAULT_OUT = "out"

SP_BY_SENT = dict()
PO_BY_SENT = dict()
SPO_BY_SENT = dict()
SENT_BY_ID = dict()
DOC_BY_ID = dict()


def get_root_word(sentence):
    return next(dep[2] for dep in sentence.dependencies if dep[1] == "root")


def get_word_with_relation(sentence, rel_target_list, rel_head="root"):
    try:
        return next(dep[2] for dep in sentence.dependencies if
                    dep[0].dependency_relation == rel_head and dep[2].dependency_relation in rel_target_list)
    except StopIteration:
        return None


def get_related_words(sentence, word):
    """
    Assumption: `word` is not None

    :param sentence:
    :param word:
    :return:
    """
    related = [dep[2] for dep in sentence.dependencies if dep[0] == word]
    related.append(word)
    return related


def sort_word_list(word_list):
    return list(sorted(word_list, key=lambda x: int(x.index)))


def get_str_from_related_words(related_words):
    sorted_list = sort_word_list(related_words)
    return " ".join(x.text for x in sorted_list)


def parse_sentence(sentence):
    obj = get_word_with_relation(sentence, DEP_REL_OBJ)
    subj = get_word_with_relation(sentence, DEP_REL_SUBJ)
    root = get_root_word(sentence)
    result = dict(sp=None, po=None, spo=None)
    if subj:
        related_subj = get_related_words(sentence, subj)
        result["sp"] = (related_subj, root)
    if obj:
        related_obj = get_related_words(sentence, obj)
        result["po"] = (root, related_obj)
    if obj and subj:
        result["spo"] = (related_subj, root, related_obj)
    return result


def process_document(pipeline, document):
    nlp_doc = pipeline(document.content)

    document.sentences = nlp_doc.sentences
    for sent in nlp_doc.sentences:
        SENT_BY_ID[id(sent)] = sent
        result = parse_sentence(sent)

        if result["sp"]:
            SP_BY_SENT[id(sent)] = result["sp"]
        if result["po"]:
            PO_BY_SENT[id(sent)] = result["po"]
        if result["spo"]:
            SPO_BY_SENT[id(sent)] = result["spo"]


def write_output(out_dir):
    """
    Write output to out_dir.
    File structure:
    - Document ID
    - Lemmatized predicate
    - Subject/object (single or pair)
    - Text
    """
    f_sp = open(os.path.join(out_dir, "sp.txt"), "w")
    f_po = open(os.path.join(out_dir, "po.txt"), "w")
    f_spo = open(os.path.join(out_dir, "spo.txt"), "w")

    for doc_id, doc in DOC_BY_ID.items():
        for sent in doc.sentences:
            sent_id = id(sent)
            s_ent = None
            s_phrase = None
            o_ent = None
            o_phrase = None

            if sent_id in SP_BY_SENT:
                s_phrase = get_str_from_related_words(SP_BY_SENT[sent_id][0])
                s_ent = next((t.mesh for t in doc.tags if t.text in s_phrase), None)

            if sent_id in PO_BY_SENT:
                o_phrase = get_str_from_related_words(PO_BY_SENT[sent_id][1])
                o_ent = next((t.mesh for t in doc.tags if t.text in o_phrase), None)

            if s_ent and s_ent != -1:
                output_sp = s_phrase + ", " + SP_BY_SENT[sent_id][1].text
                f_sp.write("{}\t{}\t{}\t{}\n".format(doc_id, SP_BY_SENT[sent_id][1].lemma, s_ent, output_sp))

            if o_ent and o_ent != -1:
                output_po = PO_BY_SENT[sent_id][0].text + ", " + o_phrase
                f_po.write("{}\t{}\t{}\t{}\n".format(doc_id, PO_BY_SENT[sent_id][0].lemma, o_ent, output_po))

            if s_ent and o_ent and s_ent != -1 and o_ent != -1:
                output_spo = s_phrase + ", " + SPO_BY_SENT[sent_id][1].text + ", " + o_phrase
                f_spo.write("{}\t{}\t{}\t{}\t({})\n".format(
                    doc_id, SPO_BY_SENT[sent_id][1].lemma, s_ent, o_ent, output_spo))

    f_sp.close()
    f_po.close()
    f_spo.close()


def main():
    global DOC_BY_ID
    parser = argparse.ArgumentParser()
    parser.add_argument("input", default=CORPUS_DOCUMENT, help="Input file (default: {})".format(CORPUS_DOCUMENT))
    parser.add_argument("--out", default=DEFAULT_OUT, help="Directory for output (default: {})".format(DEFAULT_OUT))
    args = parser.parse_args()

    if not os.path.exists(args.out):
        os.mkdir(args.out)

    start_global = datetime.now()
    start = datetime.now()
    print("Loading Stanford NLP ...")
    nlp = stanfordnlp.Pipeline(models_dir=NLP_DATA)
    end = datetime.now()
    print("Done in {}".format(end - start))

    # Prepare documents
    print("Loading documents ...")
    start = datetime.now()
    with open(args.input) as f:
        content = f.read()
    docs = content.split("\n\n")
    docs = [TaggedDocument(doc) for doc in docs if doc]
    docs = docs[:2]  # TODO: Remove for production
    DOC_BY_ID = {doc.id: doc for doc in docs}
    end = datetime.now()
    print("Done in {}".format(end - start))

    print("Processing ...")
    start = datetime.now()
    for idx, (doc_id, doc) in enumerate(DOC_BY_ID.items()):
        print("Processing document {}/{}: {}".format(idx + 1, len(docs), doc))
        process_document(nlp, doc)
    end = datetime.now()
    print("Done in {}".format(end - start))

    print("Writing output ...")
    start = datetime.now()
    write_output(args.out)
    end = datetime.now()
    print("Done in {}".format(end - start))
    print("Completely done in {}".format(end - start_global))


# Evaluation
# print(evaluate_tagged_sentence_ratio(docs))


if __name__ == "__main__":
    main()
