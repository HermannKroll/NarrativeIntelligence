"""
Task: Extract subject-predicate and predicate-object pairs from documents

https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html

Workflow:
For each document, select the sentences which contain at least one entity.
For the set of sentences, build the NLP dependency tree.
Use lemmatization to build a set of synonyms for the predicates (e.g., is metabolized, metabolizes, ...)
"""
import os
from datetime import datetime

import stanfordnlp

from narrative.document import TaggedDocument

NLP_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/stanfordnlp_resources")
DEP_REL_OBJ = ["comp", "acomp", "ccomp", "xcomp", "obj", "dobj", "iobj", "pobj", "obl"]
DEP_REL_SUBJ = ["nsubj", "subj", "csubj", "nsubj:pass"]
CORPUS_DOCUMENT = "corpus.txt"


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
    result = [None, None, None]
    if subj:
        related_subj = get_related_words(sentence, subj)
        result[0] = (related_subj, root)
    if obj:
        related_obj = get_related_words(sentence, obj)
        result[1] = (root, related_obj)
    if obj and subj:
        result[2] = (related_subj, root, related_obj)
    return tuple(result)


def process_document(pipeline, document):
    # Create initial results consisting of tuples ( (s,p), (p,o), (s,p,o) )
    nlp_doc = pipeline(document.content)
    results = []
    for sentence in nlp_doc.sentences:
        result = parse_sentence(sentence)
        if result:
            results.append(result)

    # Add mesh terms
    for idx, result in enumerate(results):
        sp = result[0]
        po = result[1]
        spo = result[2]
        s_ent = None
        o_ent = None

        if sp:  # S-O
            s_phrase = get_str_from_related_words(sp[0])
            s_ent = next((t.mesh for t in document.tags if t.text in s_phrase), None)
        if po:  # P-O
            o_phrase = get_str_from_related_words(po[1])
            o_ent = next((t.mesh for t in document.tags if t.text in o_phrase), None)
        results[idx] = (sp, po, spo, s_ent, o_ent)
    return results


def write_output(result_dict):
    f_sp = open("sp.txt", "w")
    f_po = open("po.txt", "w")
    f_spo = open("spo.txt", "w")
    for document, results in result_dict.items():
        for idx, result in enumerate(results):
            if result[3]:
                output_sp = get_str_from_related_words(result[0][0]) + ", " + result[0][1].text
                f_sp.write("{}\t{}\t{}\t{}\n".format(document.id, idx, result[3], output_sp))

            if result[4]:
                output_po = result[1][0].text + ", " + get_str_from_related_words(result[1][1])
                f_po.write("{}\t{}\t{}\t{}\n".format(document.id, idx, result[4], output_po))

            if result[3] and result[4]:
                output_spo = get_str_from_related_words(result[2][0]) + ", " + result[2][
                    1].text + ", " + get_str_from_related_words(result[2][2])
                f_spo.write("{}\t{}\t({}, {}, {})\t({})\n".format(document.id, idx, result[3], result[2][
                    1].lemma, result[4], output_spo))
    f_sp.close()
    f_po.close()
    f_spo.close()


def main():
    start_global = datetime.now()
    start = datetime.now()
    print("Loading Stanford NLP ...")
    nlp = stanfordnlp.Pipeline(models_dir=NLP_DATA)
    # sent1 = "The need for a large-scale trial of fibrate therapy in diabetes: the rationale and design of the Fenofibrate Intervention and Event Lowering in Diabetes (FIELD) study. [ISRCTN64783481]"
    # sent2 = "Fibrates correct the typical lipid abnormalities of type 2 diabetes mellitus, yet no study, to date, has specifically set out to evaluate the role of fibrate therapy in preventing cardiovascular events in this setting. Subjects with type 2 diabetes, aged 50–75 years, were screened for eligibility to participate in a long-term trial of comicronized fenofibrate 200 mg daily compared with matching placebo to assess benefits of treatment on the occurrence of coronary and other vascular events."
    # sent3 = "Barack Obama modifies three apples while eating a pear and laughing with Biden."
    # sent4 = "Simvastatin is metabolized by CYP3A4."
    # doc = nlp(sent4)
    # for sentence in doc.sentences:
    #    parse_sentence(sentence)
    end = datetime.now()
    print("Done in {}".format(end - start))

    # Prepare documents
    print("Loading documents ...")
    start = datetime.now()
    with open(CORPUS_DOCUMENT) as f:
        content = f.read()
    docs = content.split("\n\n")
    docs = [TaggedDocument(doc) for doc in docs]
    end = datetime.now()
    print("Done in {}".format(end - start))

    print("Processing ...")
    start = datetime.now()
    result_dict = dict()
    docs_to_process = docs[0:3]
    for idx, doc in enumerate(docs_to_process):
        print("Processing document {}/{}: {}".format(idx + 1, len(docs_to_process), doc))
        results = process_document(nlp, doc)
        result_dict[doc] = results
    end = datetime.now()
    print("Done in {}".format(end - start))

    print("Writing output ...")
    start = datetime.now()
    write_output(result_dict)
    end = datetime.now()
    print("Done in {}".format(end - start))
    print("Completely done in {}".format(end - start_global))

    # Evaluation
    # print(evaluate_tagged_sentence_ratio(docs))


if __name__ == "__main__":
    main()
