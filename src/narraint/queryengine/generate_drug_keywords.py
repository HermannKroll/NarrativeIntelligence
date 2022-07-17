import ast
import random
import sys

import sqlalchemy
from typing import List
from yake import KeywordExtractor

from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, DrugKeywords
from narraint.backend.retrieve import retrieve_narrative_documents_from_database

MAX_NGRAM_WORD_SIZE = 3
NUM_KEYWORDS = 20


def generate_keywords(extractor: KeywordExtractor, text: str) -> str:
    """
    Generates a list of keywords and normalizes the score to a value between 1 and 8 for HTML style purposes.

    :param extractor: yake.KeywordExtractor
    :param text: string from which the keywords are extracted
    :return: JSON-style list as a string containing 20 keywords
    """
    #  keywords [(ngram: str, score: float)]
    keywords = extractor.extract_keywords(text)

    return_str = ""

    try:
        #  normalize data for better html visualizations
        minimum = keywords[0][1]
        denominator = keywords[-1][1] - keywords[0][1]  # max - min

        normalized_keywords = []
        for obj in keywords:
            #  inverted normalized scores (1-8) for text size
            #  lower value means higher relevance (-> inverted)
            normalized_keywords.append({obj[0]: 8 - int(((obj[1] - minimum) / denominator) * 7)})
        return_str = str(normalized_keywords)

    finally:
        return return_str


def query_drugs():
    """
    Generates for each drug (enitity_id having subject_type == "Drug") a JSON list of keywords stored as a string in the
    corresponding table (drug_keywords). 100 or less random abstracts are concatenated to create a pseudo random
    information base about each drug.

    :return: None
    """
    entity_type = "Drug"
    document_collection = "PubMed"

    extractor = KeywordExtractor(n=MAX_NGRAM_WORD_SIZE, top=NUM_KEYWORDS)

    session = SessionExtended.get()
    q = session.query(PredicationInvertedIndex.subject_id) \
        .filter(PredicationInvertedIndex.subject_type == entity_type).distinct()

    drugs: List[sqlalchemy.engine.row.Row] = q.all()  # first()#
    if drugs:
        sys.stdout.write(f"Creating keywords for {len(drugs)} drugs:      ")
    else:
        print("Could not retrieve drug ids. Exiting.")
        return

    skipped_drugs = 0
    for i in range(len(drugs)):#range(1):#
        # retrieve all document_ids for one drug
        subject_id = dict(drugs[i])["subject_id"]
        q = session.query(TagInvertedIndex.document_ids) \
            .filter(TagInvertedIndex.document_collection == document_collection) \
            .filter(TagInvertedIndex.entity_id == subject_id) \
            .filter(TagInvertedIndex.entity_type == entity_type)
        doc_ids = q.first()

        # choose up to 100 random document_ids out of all available documents to prepare the sample text
        if doc_ids:
            document_ids = ast.literal_eval(doc_ids[0])
            num_abstracts = 100 if len(document_ids) >= 100 else len(document_ids)

            document_ids = set(random.sample(document_ids, num_abstracts))  # random num_abstracts elements
        else:
            skipped_drugs += 1
            # print(f"Skipping {subject_id}: No documents found!")
            continue

        # retrieve documents by id and concatenate the abstract texts
        documents = retrieve_narrative_documents_from_database(session, document_ids, document_collection)
        text = ""
        for j in range(len(documents)):
            text += " " + documents[j].abstract

        keywords = generate_keywords(extractor, text)
        # print(keywords)

        if keywords == "":
            skipped_drugs += 1
            continue

        DrugKeywords.insert_drug_keyword_data(session, subject_id, keywords)

        # display progress
        sys.stdout.write(f"\b\b\b\b\b{i + 1:5d}")
        sys.stdout.flush()

    session.remove()
    print(f"\nFinished generating keys. Skipped {skipped_drugs} drugs.")


if __name__ == "__main__":
    query_drugs()
