import ast
import logging
import random

from sqlalchemy import and_

from kgextractiontoolbox.backend.models import Document
from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex, EntityKeywords
from narraint.queryengine.generate_drug_keywords import set_stopword_list, generate_keywords, generate_stem_dict
from narrant.entity.entityresolver import EntityResolver
from narrant.preprocessing.enttypes import DISEASE


def main():
    """
    Generates for each drug (entity_id having subject_type == "Drug") a JSON
    list of keywords stored as a string in the corresponding table
    (drug_keywords). 100 or less random abstracts are concatenated to create a
    pseudo random information base about each drug.

    :return: None
    """
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    entity_type = DISEASE
    document_collection = "PubMed"

    set_stopword_list()

    session = SessionExtended.get()

    # remove all previously stored drug keywords
    q = session.query(EntityKeywords)
    q = q.filter(EntityKeywords.entity_type == DISEASE)
    q = q.delete()
    logging.info(f"{q} previously stored Covid keywords deleted")
    session.commit()

    covid_id = "MESH:D000086382"
    long_covid_id = "MESH:C000711409"
    mecfs_id = "MESH:D015673"

    ids_to_process = [covid_id, long_covid_id, mecfs_id]

    p = Progress(total=len(ids_to_process), text="Generating keyword clouds...")
    p.start_time()

    skipped_drugs = 0
    for i, entity_id in enumerate(ids_to_process):
        q = session.query(TagInvertedIndex.document_ids)
        q = q.filter(TagInvertedIndex.document_collection == document_collection)
        q = q.filter(TagInvertedIndex.entity_id == entity_id)
        q = q.filter(TagInvertedIndex.entity_type == entity_type)
        doc_ids = q.first()

        # choose up to 100 random document_ids out of all available documents to prepare the sample text
        if doc_ids:
            document_ids = ast.literal_eval(doc_ids[0])
            num_abstracts = 1000 if len(document_ids) >= 1000 else len(document_ids)

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

        print(entity_id, entity_type)
        print(keywords)
        EntityKeywords.insert_entity_keyword_data(session, entity_id, entity_type, str(keywords))

        p.print_progress(i + 1)

    session.remove()
    p.done()


if __name__ == "__main__":
    main()
