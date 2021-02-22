import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Tuple, Dict

from sqlalchemy.dialects.postgresql import insert

from narraint.entity import enttypes
from narraint.backend.database import Session
from narraint.backend.models import Document, Tag, Tagger, DocTaggedBy
from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents
from narraint.pubtator.document import TaggedDocument
from narraint.pubtator.extract import read_pubtator_documents

BULK_LOAD_COMMIT_AFTER = 50000
PRINT_ETA_EVERY_K_DOCUMENTS = 100
UNKNOWN_TAGGER = ["Unknown", "unknown"]


def read_tagger_mapping(filename: str) -> Dict[str, Tuple[str, str]]:
    """
    Reads the tagger mapping from `filename`.

    :param str filename: Path to tagger mapping JSON file.
    :return: Dict with entity type as key and tuple consisting of tagger name and tagger version as value
    """
    with open(filename) as f:
        content = f.read()
    mapping = json.loads(content)
    for ent_type, tagger in mapping.items():
        if ent_type not in enttypes.ALL or len(tagger) != 2:
            del mapping[ent_type]
    return mapping


def get_tagger_for_enttype(tagger_mapping, ent_type):
    if ent_type not in tagger_mapping:
        return UNKNOWN_TAGGER[0], UNKNOWN_TAGGER[1]
    else:
        return tagger_mapping[ent_type][0], tagger_mapping[ent_type][1]


def insert_taggers(*tagger_list):
    """
    Inserts the taggers from the list.

    :param tagger_list: List consisting of Pairs with tagger name and tagger version
    :return:
    """
    session = Session.get()
    for tagger in tagger_list:
        insert_stmt = insert(Tagger).values(
            name=tagger[0],
            version=tagger[1],
        )
        if not Session.is_sqlite:
            insert_stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=('name', 'version'),
            )
        session.execute(insert_stmt)
    session.commit()


def document_bulk_load(path, collection, tagger_mapping=None):
    """
       Bulk load a file in PubTator Format or a directory of PubTator files into the database.
       Do not use this method for parallel load - it will not check whether conflicts exists

       Iterate over PubTator documents and add Document, Tag and DocTaggedBy objects. Commit after every document.

        :param str path: Path to file or directory
       :param str collection: Identifier of the collection (e.g., PMC)
       :param dict tagger_mapping: Mapping from entity type to tuple (tagger name, tagger version)
       :return:
       """
    session = Session.get()

    if tagger_mapping is None:
        logging.warning("No tagger mapping provided. Tags are ignored")

    logging.info('Bulk loading documents into database...')
    sys.stdout.write("Counting documents ...")
    sys.stdout.flush()
    n_docs = count_documents(path)
    sys.stdout.write("\rCounting documents ... found {}\n".format(n_docs))
    sys.stdout.flush()
    logging.info("Found {} documents".format(n_docs))

    logging.info('Retrieving document ids from database...')
    query = session.query(Document.id).filter_by(collection=collection)
    db_doc_ids = set()
    for r in session.execute(query):
        db_doc_ids.add(r[0])
    logging.info('{} documents are already inserted'.format(len(db_doc_ids)))
    start_time = datetime.now()

    document_inserts = []
    tag_inserts = []
    if not tagger_mapping:
        ignore_tags = True
    else:
        ignore_tags = False

    doc_tagged_by_inserts = []
    for idx, pubtator_content in enumerate(read_pubtator_documents(path)):
        doc = TaggedDocument(pubtator_content, ignore_tags=ignore_tags)
        tagged_ent_types = set()
        # skip included documents
        if doc.id in db_doc_ids:
            continue

        # Add document if its not already included
        if doc.title:
            db_doc_ids.add(doc.id)
            document_inserts.append(dict(
                collection=collection,
                id=doc.id,
                title=doc.title,
                abstract=doc.abstract,
            ))

        if doc.id not in db_doc_ids:
            logging.warning("Document {} {} not in DB".format(collection, doc.id))
        # only if tagger mapping is set, tags will be inserted
        if doc.tags and tagger_mapping and doc.id in db_doc_ids:
            # Add tags
            for tag in doc.tags:
                tagged_ent_types.add(tag.ent_type)

                tag_inserts.append(dict(
                    ent_type=tag.ent_type,
                    start=tag.start,
                    end=tag.end,
                    ent_id=tag.ent_id,
                    ent_str=tag.text,
                    document_id=tag.document,
                    document_collection=collection,
                ))

            # Add DocTaggedBy
            for ent_type in tagged_ent_types:
                tagger_name, tagger_version = get_tagger_for_enttype(tagger_mapping, ent_type)
                doc_tagged_by_inserts.append(dict(
                    document_id=doc.id,
                    document_collection=collection,
                    tagger_name=tagger_name,
                    tagger_version=tagger_version,
                    ent_type=ent_type,
                ))

        if idx % BULK_LOAD_COMMIT_AFTER == 0:
            session.bulk_insert_mappings(Document, document_inserts)
            session.bulk_insert_mappings(Tag, tag_inserts)
            session.bulk_insert_mappings(DocTaggedBy, doc_tagged_by_inserts)

            document_inserts = []
            tag_inserts = []
            doc_tagged_by_inserts = []
            session.commit()
        print_progress_with_eta("Adding documents", idx, n_docs, start_time, print_every_k=PRINT_ETA_EVERY_K_DOCUMENTS)

    session.bulk_insert_mappings(Document, document_inserts)
    session.bulk_insert_mappings(Tag, tag_inserts)
    session.bulk_insert_mappings(DocTaggedBy, doc_tagged_by_inserts)
    session.commit()

    sys.stdout.write("\rAdding documents ... done in {}\n".format(datetime.now() - start_time))
    logging.info("Added {} documents in {}".format(n_docs, datetime.now() - start_time))


def load_document(path, collection, tagger_mapping=None, logger=None):
    """
    Load a file in PubTator Format or a directory of PubTator files into the database.
    Works if multiple inserts run parallel

    Iterate over PubTator documents and add Document, Tag and DocTaggedBy objects. Commit after every document.

     :param str path: Path to file or directory
    :param str collection: Identifier of the collection (e.g., PMC)
    :param dict tagger_mapping: Mapping from entity type to tuple (tagger name, tagger version)
    :param logging logger: a logging instance to be used
    :return:
    """
    session = Session.get()

    if tagger_mapping is None:
        # if logger: logger.warning("No tagger mapping provided. Tags are ignored")
        logging.warning("No tagger mapping provided. Tags are ignored")

    if logger: logger.info('Load documents into database...')
    if logger: logger.info("Counting documents ...")
    sys.stdout.flush()
    n_docs = count_documents(path)
    if logger: logger.info("Counting documents ... found {}".format(n_docs))
    sys.stdout.flush()
    if logger: logger.info("Found {} documents".format(n_docs))

    if not tagger_mapping:
        ignore_tags = True
    else:
        ignore_tags = False
    start_time = datetime.now()
    for idx, pubtator_content in enumerate(read_pubtator_documents(path)):
        doc = TaggedDocument(pubtator_content, ignore_tags=ignore_tags)
        tagged_ent_types = set()
        # Add document
        if doc.title:
            insert_document = insert(Document).values(
                collection=collection,
                id=doc.id,
                title=doc.title,
                abstract=doc.abstract,
            )
            if not Session.is_sqlite:
                insert_document = insert_document.on_conflict_do_nothing(
                    index_elements=('collection', 'id')
                )
            session.execute(insert_document)

        # only if tagger mapping is set, tags will be inserted
        if doc.tags and tagger_mapping:
            q_exists = session.query(Document) \
                .filter(Document.id == doc.id, Document.collection == collection).exists()
            if session.query(q_exists).scalar():
                # Add tags
                for tag in doc.tags:
                    tagged_ent_types.add(tag.ent_type)

                    insert_tag = insert(Tag).values(
                        ent_type=tag.ent_type,
                        start=tag.start,
                        end=tag.end,
                        ent_id=tag.ent_id,
                        ent_str=tag.text,
                        document_id=tag.document,
                        document_collection=collection,
                    )
                    if not Session.is_sqlite:
                        insert_tag = insert_tag.on_conflict_do_nothing(
                            index_elements=('document_id', 'document_collection', 'start', 'end', 'ent_type', 'ent_id'),
                        )
                    session.execute(insert_tag)

                # Add DocTaggedBy
                for ent_type in tagged_ent_types:
                    tagger_name, tagger_version = get_tagger_for_enttype(tagger_mapping, ent_type)
                    insert_doc_tagged_by = insert(DocTaggedBy).values(
                        document_id=doc.id,
                        document_collection=collection,
                        tagger_name=tagger_name,
                        tagger_version=tagger_version,
                        ent_type=ent_type,
                    )
                    if not Session.is_sqlite:
                        insert_doc_tagged_by = insert_doc_tagged_by.on_conflict_do_nothing(
                            index_elements=('document_id', 'document_collection',
                                            'tagger_name', 'tagger_version', 'ent_type'),
                        )
                    session.execute(insert_doc_tagged_by)
            else:
                if logger: logger.warning("Document {} {} not in DB".format(collection, doc.id))

        session.commit()
        if logger: print_progress_with_eta("Adding documents", idx, n_docs, start_time,
                                           print_every_k=PRINT_ETA_EVERY_K_DOCUMENTS,
                                           logger=logger)

    if logger: logger.info("Added documents in {}".format(datetime.now() - start_time))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("collection")
    parser.add_argument("-b", "--bulk", action="store_true", help="Enforcing bulk load - Duplicated documents "
                                                                  "will be skipped. WARNING: will not handle errors if"
                                                                  " duplicate values are inserted, "
                                                                  "e.g. tags already exists. ")
    parser.add_argument("-t", "--tagger-map", help="JSON file containing mapping from entity type "
                                                   "to tuple with tagger name and tagger version")
    parser.add_argument("--logsql", action="store_true", help='logs sql statements')
    args = parser.parse_args()

    tagger_mapping = None
    if args.tagger_map:
        tagger_mapping = read_tagger_mapping(args.tagger_map)
        tagger_list = list(tagger_mapping.values())
        tagger_list.append(UNKNOWN_TAGGER)
        insert_taggers(*tagger_list)

    if args.logsql:
        logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%Y-%m-%d:%H:%M:%S',
                            level=logging.INFO)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    else:
        logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%Y-%m-%d:%H:%M:%S',
                            level=logging.INFO)

    if args.bulk:
        document_bulk_load(args.input, args.collection, tagger_mapping)
    else:
        load_document(args.input, args.collection, tagger_mapping)


if __name__ == "__main__":
    main()
