import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Tuple, Dict, Set

from sqlalchemy.dialects.postgresql import insert

from narraint.backend import enttypes
from narraint.backend.database import Session
from narraint.backend.models import Document, Tag, Tagger, DocTaggedBy
from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS, TAG_LINE_NORMAL, TAG_DOCUMENT_ID

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


def insert_taggers(tagger_list):
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
        ).on_conflict_do_nothing(
            index_elements=('name', 'version'),
        )
        session.execute(insert_stmt)
    session.commit()


def get_id_content_tag(pubtator_content: str) -> Tuple[int, Tuple[int, str, str], Set]:
    """
    Get document ID, title, abstract and tags from PubTator document. Selects only the FIRST document.

    :param pubtator_content: Input PubTator content
    :return: Triple consisting of document ID, Triple consisting of Id, title, abstract and tags
    """
    m_tags = TAG_LINE_NORMAL.findall(pubtator_content)
    m_documents = CONTENT_ID_TIT_ABS.findall(pubtator_content)
    if m_documents:
        document_id = int(m_documents[0][0])
    else:
        m_tag_doc_id = TAG_DOCUMENT_ID.search(pubtator_content)
        document_id = int(m_tag_doc_id.group(1)) if m_tag_doc_id else None
    document = (int(m_documents[0][0]), m_documents[0][1].strip(), m_documents[0][2].strip()) if m_documents else None
    tags = set((int(m[0]), int(m[1]), int(m[2]), m[3].strip(), m[4].strip(), m[5].strip()) for m in m_tags if
               int(m[0]) == document_id)
    return document_id, document, tags


def bulk_load(path, collection, logger, tagger_mapping=None):
    """
    Bulk load a file in PubTator Format or a directory of PubTator files into the database.

    Iterate over PubTator documents and add Document, Tag and DocTaggedBy objects. Commit after every document.

    :param logger: Logger instance
    :param str path: Path to file or directory
    :param str collection: Identifier of the collection (e.g., PMC)
    :param dict tagger_mapping: Mapping from entity type to tuple (tagger name, tagger version)
    :return:
    """
    session = Session.get()

    if tagger_mapping is None:
        logger.warning("No tagger mapping provided. Tags are ignored")

    sys.stdout.write("Counting documents ...")
    sys.stdout.flush()
    n_docs = count_documents(path)
    sys.stdout.write("\rCounting documents ... found {}\n".format(n_docs))
    sys.stdout.flush()
    logger.info("Found {} documents".format(n_docs))

    start_time = datetime.now()
    for idx, pubtator_content in enumerate(read_pubtator_documents(path)):
        tagged_ent_types = set()
        doc_id, d_content, d_tags = get_id_content_tag(pubtator_content)

        # Add document
        if d_content:
            insert_document = insert(Document).values(
                collection=collection,
                id=d_content[0],
                title=d_content[1],
                abstract=d_content[2],
            ).on_conflict_do_nothing(
                index_elements=('collection', 'id'),
            )
            session.execute(insert_document)

        # only if tagger mapping is set, tags will be inserted
        if d_tags and tagger_mapping:
            q_exists = session.query(Document) \
                .filter(Document.id == doc_id, Document.collection == collection).exists()
            if session.query(q_exists).scalar():
                # Add tags
                for d_id, start, end, ent_str, ent_type, ent_id in d_tags:
                    tagger_name, tagger_version = get_tagger_for_enttype(tagger_mapping, ent_type)
                    tagged_ent_types.add(ent_type)

                    insert_tag = insert(Tag).values(
                        ent_type=ent_type,
                        start=start,
                        end=end,
                        ent_id=ent_id,
                        ent_str=ent_str,
                        document_id=d_id,
                        document_collection=collection,
                        tagger_name=tagger_name,
                        tagger_version=tagger_version,
                    ).on_conflict_do_nothing(
                        index_elements=('document_id', 'document_collection', 'start', 'end', 'ent_type', 'ent_id'),
                    )
                    session.execute(insert_tag)

                # Add DocTaggedBy
                for ent_type in tagged_ent_types:
                    tagger_name, tagger_version = get_tagger_for_enttype(tagger_mapping, ent_type)
                    insert_doc_tagged_by = insert(DocTaggedBy).values(
                        document_id=doc_id,
                        document_collection=collection,
                        tagger_name=tagger_name,
                        tagger_version=tagger_version,
                        ent_type=ent_type,
                    ).on_conflict_do_nothing(
                        index_elements=('document_id', 'document_collection',
                                        'tagger_name', 'tagger_version', 'ent_type'),
                    )
                    session.execute(insert_doc_tagged_by)
            else:
                logger.warning("Document {} {} not in DB".format(collection, doc_id))

        session.commit()
        print_progress_with_eta("Adding documents", idx, n_docs, start_time, print_every_k=PRINT_ETA_EVERY_K_DOCUMENTS)

    sys.stdout.write("\rAdding documents ... done in {}\n".format(datetime.now() - start_time))
    logger.info("Added documents in {}".format(datetime.now() - start_time))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("collection")
    parser.add_argument("-t", "--tagger-map", help="JSON file containing mapping from entity type "
                                                   "to tuple with tagger name and tagger version")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    tagger_mapping = None
    if args.tagger_map:
        tagger_mapping = read_tagger_mapping(args.tagger_map)
        tagger_list = list(tagger_mapping.values())
        tagger_list.append(UNKNOWN_TAGGER)
        insert_taggers(tagger_list)

    if args.log:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logger = logging.getLogger(__name__).setLevel(logging.INFO)
    else:
        logger = logging.getLogger(__name__).setLevel(logging.CRITICAL)

    bulk_load(args.input, args.collection, logger, tagger_mapping)


if __name__ == "__main__":
    main()
