"""
Test document retrieval using a Narrative and a document.
"""
import argparse
import hashlib
import os
import pickle
from datetime import datetime

from narrative.document import TaggedDocument
from narrative.overlay import FactPattern, Substory, Event, Narrative
from processor import QueryProcessor


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def filter_corpus(corpus_in, corpus_out, id_list_or_file):
    if isinstance(id_list_or_file, str):
        with open(id_list_or_file) as f:
            lines = f.readlines()
        id_set = set(line.strip() for line in lines)
    else:
        id_set = set(id_list_or_file)

    with open(corpus_in) as f:
        content = f.read()
    documents = content.split("\n\n")
    with open(corpus_out, "w") as f:
        for document in documents:
            if document:
                did = document[0:document.index("|")]
                if did in id_set or "PMC{}".format(did) in id_set:
                    f.write(document + "\n\n")


def load_documents(filename):
    app_data = ".docs"
    if not os.path.exists(app_data):
        os.mkdir(app_data)
    md5_sum = md5(filename)
    pickle_path = os.path.join(app_data, "{}.pickle".format(md5_sum))
    print("Loading documents ...")
    start = datetime.now()
    if os.path.exists(pickle_path):
        print("Using document collection {}".format(pickle_path))
        with open(pickle_path, "rb") as f:
            docs = pickle.load(f)
    else:
        with open(filename) as f:
            content = f.read()
        docs = content.split("\n\n")
        step = datetime.now()
        print("Read {} documents in {}".format(len(docs) - 1, step - start))
        docs = [TaggedDocument(doc) for doc in docs if doc]

        print("Writing documents to {}".format(pickle_path))
        with open(pickle_path, "wb") as f:
            pickle.dump(docs, f)
    end = datetime.now()
    print("Done in {}. {} per document".format(end - start, (end - start) / len(docs)))
    return docs


def main():
    # Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file")
    parser.add_argument("--out", default="out", help="Directory for output (default: out)")
    parser.add_argument("--ami", action="store_true")
    parser.add_argument("--ery", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.out):
        os.mkdir(args.out)

    # Load documents
    docs = load_documents(args.input)

    # Create Narrative _query
    fp1 = FactPattern("1576", "metaboli", "MESH:D019821", "Gene", "Chemical")
    fp2_ami = FactPattern("MESH:D000638", "inhibit", "1576", "Chemical", "Gene")
    fp2_ery = FactPattern("MESH:D004917", "inhibit", "1576", "Chemical", "Gene")
    ss_ery = Substory(fp1, fp2_ery)
    ss_ami = Substory(fp1, fp2_ami)
    e1 = Event(r"(accum)|"
               r"((increas|elevate).*(level|plasma.*concentration))|"
               r"((level|plasma.*concentration).*(increas|elevate))",
               "MESH:D019821", "Chemical")
    e2 = Event("(increas.*risk)|(risk.*increas)|(higher risk)", "?x", "Disease")
    q_ami = Narrative(
        (ss_ami, "leads_to", e1),
        (e1, "leads_to", e2),
    )
    q_ery = Narrative(
        (ss_ery, "leads_to", e1),
        (e1, "leads_to", e2),
    )

    # Match
    qp = QueryProcessor(*docs)
    if args.ami:
        qp.query(q_ami)
        qp.print_result("results_amiodarone.log")
        qp.print_debug("debug_amiodarone.log", True)
    if args.ery:
        qp.query(q_ery)
        qp.print_result("results_erythromycin.log")
        qp.print_debug("debug_erythromycin.log", True)


if __name__ == "__main__":
    main()
