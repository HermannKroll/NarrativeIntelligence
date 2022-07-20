import ast
import random
import sys

import sqlalchemy
from typing import List

from sqlalchemy import and_
from yake import KeywordExtractor

from kgextractiontoolbox.backend.models import Document
from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, EntityKeywords

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


def main():
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
        sys.stdout.write(f"Creating keywords for {len(drugs)} drugs\n")
    else:
        print("Could not retrieve drug ids. Exiting.")
        return

    p = Progress(total=len(drugs))
    p.start_time()

    skipped_drugs = 0
    for i in range(len(drugs)):  # range(1):#
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
            continue

        # query document abstract
        doc_query = session.query(Document.abstract).filter(and_(Document.id.in_(document_ids),
                                                                 Document.collection == document_collection))
        text = []

        for res in doc_query:
            text.append(res[0])

        text = " ".join([t for t in text])

        keywords = generate_keywords(extractor, text)
        # print(keywords)

        if keywords == "":
            skipped_drugs += 1
            continue

        EntityKeywords.insert_entity_keyword_data(session, subject_id, entity_type, keywords)
        p.print_progress(i + 1)

    session.remove()
    p.done()
    print(f"Skipped {skipped_drugs} drugs.")


if __name__ == "__main__":
    main()
