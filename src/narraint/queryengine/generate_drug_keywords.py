import ast
import random

import sqlalchemy
from typing import List

from sqlalchemy import and_
from yake import KeywordExtractor
from nltk.stem.porter import PorterStemmer

from kgextractiontoolbox.backend.models import Document
from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, EntityKeywords
from narrant.entity.entityresolver import EntityResolver

# used to switch between table access and debugging console prints
ACCESS_ENTITY_KEYWORDS_TABLE = True

MAX_NGRAM_WORD_SIZE = 1
NUM_KEYWORDS = 25

extractor = KeywordExtractor(n=MAX_NGRAM_WORD_SIZE, top=NUM_KEYWORDS, dedupLim=0.9, dedupFunc="jaro")
stemmer = PorterStemmer()


def generate_stem_dict(text: str) -> dict[str, str]:
    """
    Generates a dict containing a pair of the word stem and the shortest word
    which results the corresponding stem.

    :param text: string to evaluate
    :return: dict with stem - word combination
    """
    stem_dict = dict()

    # remove all unwanted chars
    mapping = text.maketrans('','',',.!?":\'*+')
    text = text.translate(mapping)

    for word in set(text.split(' ')):
        temp = stemmer.stem(word)
        if temp in stem_dict.keys():
            if len(stem_dict[temp]) > len(word):
                stem_dict[temp] = word
            continue
        stem_dict[temp] = word

    return stem_dict


def generate_keywords(text: str, entity_name: str, stem_dict: dict) -> str:
    """
    Generates a list of keywords and normalizes the score to a value between 1
    and 8 for HTML style purposes.

    :param text: string from which the keywords are extracted
    :param entity_name: name of the current entity to ignore it as a key
    :param stem_dict: dictionary word stem with the shortest stemmed word
    :return: JSON-style list as a string containing 20 keywords
    """
    # raw_keywords [(ngram: str, score: float)]
    raw_keywords = extractor.extract_keywords(text)
    keyword_map = list()
    keywords = set()
    normalized_keywords = list()
    try:
        for keyword, score in raw_keywords:
            # ignore already known keywords
            if keyword in keywords:
                continue
            # ignore the key if it is part of the entity_name
            if entity_name.lower().find(keyword.lower()) >= 0 \
                    or entity_name.lower() == keyword.lower():
                continue
            # replace keywords with the most likely stem
            stem = stemmer.stem(keyword)
            if stem in stem_dict.keys():
                if len(stem) + 1 == len(stem_dict[stem]) \
                        and stem_dict[stem][-1] == 's'\
                        and stem not in keywords:
                    keyword_map.append((stem, score))
                    keywords.add(stem)
                elif stem_dict[stem] not in keywords:
                    keyword_map.append((stem_dict[stem], score))
                    keywords.add(stem_dict[stem])
            else:
                keyword_map.append((keyword, score))
                keywords.add(keyword)

        # use the 20 first highest valued keys
        if len(keyword_map) > 20:
            keyword_map = keyword_map[:20]

        # normalize data for better html visualizations
        minimum = keyword_map[0][1]
        denominator = keyword_map[-1][1] - keyword_map[0][1]  # max - min

        for obj in keyword_map:
            #  inverted normalized scores (1-8) for text size
            #  lower value means higher relevance (-> inverted)
            normalized_keywords.append({obj[0]: 8 - int(((obj[1] - minimum) /
                                                         denominator) * 7)})

    finally:
        return str(normalized_keywords)


def main():
    """
    Generates for each drug (entity_id having subject_type == "Drug") a JSON
    list of keywords stored as a string in the corresponding table
    (drug_keywords). 100 or less random abstracts are concatenated to create a
    pseudo random information base about each drug.

    :return: None
    """
    entity_type = "Drug"
    document_collection = "PubMed"

    session = SessionExtended.get()

    if ACCESS_ENTITY_KEYWORDS_TABLE:
        # remove all previously stored drug keywords
        q = session.query(EntityKeywords)
        q = q.filter(EntityKeywords.entity_type == "Drug")
        q = q.delete()
        print(f"{q} previously stored DRUG keywords deleted")
        session.commit()

    # query all existing drug entities
    q = session.query(PredicationInvertedIndex.subject_id)
    q = q.filter(PredicationInvertedIndex.subject_type == entity_type)
    q = q.distinct()

    drugs: List[sqlalchemy.engine.row.Row] = q.all()  # first()#
    if drugs:
        print(f"Creating keywords for {len(drugs)} drugs")
    else:
        print("Could not retrieve drug ids. Exiting.")
        return

    p = Progress(total=len(drugs))
    p.start_time()

    skipped_drugs = 0
    for i in range(len(drugs)):  #range(10):#
        # retrieve all document_ids for one drug
        entity_id = dict(drugs[i])["subject_id"]
        q = session.query(TagInvertedIndex.document_ids)
        q = q.filter(TagInvertedIndex.document_collection == document_collection)
        q = q.filter(TagInvertedIndex.entity_id == entity_id)
        q = q.filter(TagInvertedIndex.entity_type == entity_type)
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
        entity_name = EntityResolver.instance().get_name_for_var_ent_id(entity_id, entity_type)
        stem_dict = generate_stem_dict(text)
        keywords = generate_keywords(text, entity_name, stem_dict)
        if keywords == "[]":
            skipped_drugs += 1
            continue

        if ACCESS_ENTITY_KEYWORDS_TABLE:
            EntityKeywords.insert_entity_keyword_data(session, entity_id, entity_type, str(keywords))
        else:
            print("\n", i, entity_name, keywords)

        p.print_progress(i + 1)

    session.remove()
    p.done()
    print(f"Skipped {skipped_drugs} drugs.")


if __name__ == "__main__":
    main()
