import logging
import random
import string
from argparse import ArgumentParser

from kgextractiontoolbox.backend.models import Document, Tag, Sentence, Predication
from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.delete_collection import delete_document_collection_from_database_enhanced
from narraint.backend.util import get_db_connection_name

NUMBER_OF_ENTITIES = 100000
NUMBER_OF_ENTITY_TYPES = 10
NUMBER_OF_RELATIONS = 10


def get_random_entity_id():
    return "entity_id_" + str(random.randint(0, NUMBER_OF_ENTITIES))


def get_random_entity_type():
    return "entity_type_" + str(random.randint(0, NUMBER_OF_ENTITY_TYPES))


def get_random_relation():
    return "relation_" + str(random.randint(0, NUMBER_OF_RELATIONS))


def get_random_string(min_length: int, max_length: int):
    length = random.randint(min_length, max_length)
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return result_str


def generate_dummy_db_data(number_of_documents: int, collection: str, incremental: bool):
    if not number_of_documents:
        raise ValueError('Number of documents must be > 0')

    session = SessionExtended.get()

    document_values = []
    tag_values = []
    predication_values = []
    sentence_values = []

    sentence_id = Sentence.query_highest_sentence_id(session) + 1
    if incremental:
        doc_offset = Document.query_highest_document_id(session, document_collection=collection) + 1
    else:
        doc_offset = 0

    logging.info(f'Next sentence id is: {sentence_id}')
    logging.info(f'Next document id is: {doc_offset}')
    logging.info('-' * 60)
    logging.info('-' * 60)
    logging.info('Beginning generation phase')
    progress = Progress(total=number_of_documents, print_every=100, text="Generating DB data")
    progress.start_time()
    for doc_idx in range(0, number_of_documents):
        progress.print_progress(doc_idx)
        document_values.append(dict(id=doc_offset + doc_idx,
                                    collection=collection,
                                    title=get_random_string(20, 50),
                                    abstract=get_random_string(300, 500)))

        # Every document has 0... to 20 tags
        for tag_idx in range(0, random.randint(0, 20)):
            tag_values.append(dict(ent_type=get_random_entity_type(),
                                   start=random.randint(0, 300),
                                   end=random.randint(0, 300),
                                   ent_id=get_random_entity_id(),
                                   ent_str=get_random_string(5, 50),
                                   document_id=doc_idx,
                                   document_collection=collection))

        # Every document has 1... to 10 sentences
        sentences_to_generate = random.randint(1, 10)
        for sent_idx in range(0, sentences_to_generate):
            sentence_values.append(dict(
                id=sentence_id,
                document_collection=collection,
                text=get_random_string(10, 100),
                md5hash=get_random_string(20, 20)
            ))
            sentence_id += 1

        # Every document has 0... to 20 tags
        for predication_idx in range(0, random.randint(0, 20)):
            predication_values.append(dict(
                document_id=doc_idx,
                document_collection=collection,
                subject_id=get_random_entity_id(),
                subject_str=get_random_string(5, 50),
                subject_type=get_random_entity_type(),
                predicate=get_random_string(5, 50),
                relation=get_random_relation(),
                object_id=get_random_entity_id(),
                object_str=get_random_string(5, 50),
                object_type=get_random_entity_type(),
                confidence=random.random(),
                sentence_id=random.randint(1, sentences_to_generate),
                extraction_type="random"
            ))

        # Insert every 10000 documents
        if doc_idx > 0 and doc_idx % 10000 == 0:
            print()
            logging.info(f'Inserting {len(document_values)} documents /'
                         f' {len(tag_values)} tags /'
                         f' {len(sentence_values)} sentences /'
                         f' {len(predication_values)} predications')
            Document.bulk_insert_values_into_table(session, document_values)
            Tag.bulk_insert_values_into_table(session, tag_values)
            Sentence.bulk_insert_values_into_table(session, sentence_values)
            Predication.bulk_insert_values_into_table(session, predication_values)

            document_values.clear()
            tag_values.clear()
            sentence_values.clear()
            predication_values.clear()

    # Insert Remaining data
    print()
    logging.info(f'Inserting {len(document_values)} documents /'
                 f' {len(tag_values)} tags /'
                 f' {len(sentence_values)} sentences /'
                 f' {len(predication_values)} predications')

    Document.bulk_insert_values_into_table(session, document_values)
    Tag.bulk_insert_values_into_table(session, tag_values)
    Sentence.bulk_insert_values_into_table(session, sentence_values)
    Predication.bulk_insert_values_into_table(session, predication_values)

    progress.done()
    logging.info('-' * 60)
    logging.info('-' * 60)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    parser = ArgumentParser(description="Generate dummy data for the DB for test purposes")
    parser.add_argument('number_of_documents', type=int, help="Number of documents that should be generated")
    parser.add_argument('--incremental', action="store_true", help="Don't delete data and just add incremental data")
    args = parser.parse_args()

    document_collection = "DUMMY_GENERATOR"
    if not args.incremental:
        logging.info('=' * 70)
        logging.info('=' * 70)
        logging.info('=' * 70)
        logging.info('========== Be careful right now - The script will delete DB data ===========')
        logging.info('=' * 70)
        logging.info('=' * 70)
        logging.info('=' * 70)
        database_name = get_db_connection_name()
        logging.info(f'Your current database is: {database_name}')

        session = SessionExtended.get()
        doc_count = session.query(Document.id.distinct()).filter(Document.collection == document_collection).count()
        logging.info('{} documents found in collection {}'.format(doc_count, document_collection))
        print('{} documents are found'.format(doc_count))
        print(f'Are you really want to delete documents in collection {document_collection}? '
              f'This will also delete all corresponding tags (Tag), '
              'tagging information (doc_taggedb_by), facts (Predication) and extraction information (doc_processed_by_ie)')
        answer = input('Enter y(yes) to proceed the deletion...')
        if (answer and (answer.lower() == 'y' or answer.lower() == 'yes')):
            delete_document_collection_from_database_enhanced(document_collection)
            logging.info('Finished')
        else:
            print('Canceled')
    else:
        logging.info(f'Adding incremental data to collection: {document_collection}')

    generate_dummy_db_data(int(args.number_of_documents), document_collection, args.incremental)


if __name__ == "__main__":
    main()
