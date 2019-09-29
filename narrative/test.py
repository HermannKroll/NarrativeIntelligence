"""
Test document retrieval using a Narrative and a document.
"""
import argparse
import os
from datetime import datetime

from narrative.document import TaggedDocument
from narrative.overlay import FactPattern, Substory, Event, Narrative
from processor import QueryProcessor


def main():
    # Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file")
    parser.add_argument("--out", default="out", help="Directory for output (default: out)")
    args = parser.parse_args()

    if not os.path.exists(args.out):
        os.mkdir(args.out)

    # Load documents
    print("Loading documents ...")
    start = datetime.now()
    with open(args.input) as f:
        content = f.read()
    docs = content.split("\n\n")
    docs = [TaggedDocument(doc) for doc in docs if doc]
    end = datetime.now()
    print("Done in {}. {} per document".format(end - start, (end - start) / len(docs)))

    # Create Narrative _query
    fp1 = FactPattern("CYP3A4", "metaboli", "Simvastatin", "Gene", "Chemical")
    fp2 = FactPattern("?y", "inhibit", "CYP3A4", "Chemical", "Gene")
    ss = Substory(fp1, fp2)
    e1 = Event("accumulat", "Simvastatin", "Chemical")
    e2 = Event("increas", "?x", "Disease")
    query = Narrative(
        (ss, "leads_to", e1),
        (e1, "leads_to", e2),
    )

    # Match
    print("Matching documents ...")
    qp = QueryProcessor(*docs)
    qp.query(query)
    qp.print_result()


if __name__ == "__main__":
    main()
