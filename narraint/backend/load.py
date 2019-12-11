import argparse
import logging
import os
import sys
from datetime import datetime

from narraint.backend.database import Session
from narraint.backend.models import Document, Tag
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS, TAG_LINE_NORMAL, CONTENT_RAW


# TODO: Ignore empty tags
def bulk_load(path, collection, tagger=None):
    """
    Bulk load a file in PubTator Format or a directory of PubTator files into the database.

    :param str or None tagger: Name of the used tagger
    :param str collection: Identifier of the collection (e.g., PMC)
    :param str path: Path to file or directory
    :return:
    """
    sys.stdout.write("Reading files ...")
    sys.stdout.flush()
    if os.path.isdir(path):
        files = [os.path.join(path, fn) for fn in os.listdir(path) if not fn.startswith(".") and fn.endswith(".txt")]
        content_list = []
        for fn in files:
            with open(fn) as f:
                content_list.append(f.read())
    else:
        with open(path) as f:
            content = f.read()
        content_list = CONTENT_RAW.findall(content)

    document_ids = set()
    documents = set()
    tags = set()
    for text in content_list:
        m_tags = TAG_LINE_NORMAL.findall(text)
        m_documents = CONTENT_ID_TIT_ABS.findall(text)
        document_ids.update(int(m[0]) for m in m_documents)
        documents.update((int(m[0]), m[1].strip(), m[2].strip()) for m in m_documents)
        tags.update((int(m[0]), int(m[1]), int(m[2]), m[3].strip(), m[4].strip(), m[5].strip()) for m in m_tags)
    total_items = len(documents) + len(tags)
    sys.stdout.write(" {} documents and {} tags\n".format(len(documents), len(tags)))

    sys.stdout.write("Retrieving ... ")
    sys.stdout.flush()

    session = Session.get()
    session.execute("LOCK TABLE document IN EXCLUSIVE MODE")
    session.execute("LOCK TABLE tag IN EXCLUSIVE MODE")
    db_document_ids = set(
        x[0] for x in session.query(Document).filter(Document.collection == collection).values(Document.id))
    db_tags = set(session.query(Tag).filter(Tag.document_collection == collection).values(
        Tag.document_id, Tag.start, Tag.end, Tag.ent_str, Tag.type, Tag.ent_id,
    ))
    sys.stdout.write("\rRetrieving ... {} documents and {} tags\n".format(len(db_document_ids), len(db_tags)))
    sys.stdout.flush()

    sys.stdout.write("Preparing ... 0.0 %")
    sys.stdout.flush()
    start = datetime.now()
    for idx, doc in enumerate(documents):
        if doc[0] not in db_document_ids:
            session.add(Document(
                id=doc[0],
                collection=collection,
                title=doc[1],
                abstract=doc[2],
                date_inserted=datetime.now(),
            ))
        sys.stdout.write("\rPreparing ... {:0.1f} %".format((idx + 1.0) / total_items * 100.0))
        sys.stdout.flush()
    for idx, tag in enumerate(tags):
        if tag not in db_tags:
            session.add(Tag(
                start=tag[1],
                end=tag[2],
                type=tag[4],
                ent_str=tag[3],
                ent_id=tag[5],
                document_id=tag[0],
                document_collection=collection,
                tagger=tagger,
            ))
        sys.stdout.write("\rPreparing ... {:0.1f} %".format((len(documents) + idx + 1.0) / total_items * 100.0))
        sys.stdout.flush()
    sys.stdout.write("\rPreparing ... done in {}\nCommitting ...".format(datetime.now() - start))
    sys.stdout.flush()
    start = datetime.now()
    session.commit()
    sys.stdout.write(" done in {}\n".format(datetime.now() - start))
    sys.stdout.flush()


def tag_kwargs_from_match(m, collection):
    return dict(
        type=m[4],
        start=int(m[1]),
        end=int(m[2]),
        ent_id=m[5],
        ent_str=m[3],
        document_id=int(m[0]),
        document_collection=collection,
    )


def load_single(content, collection, tagger=None):
    """
    Loads a single PubTator file into the database. The method is designed to make as few database calls as possible.
    The method selects the document part (title + abstract) from the file using regular expressions and then
    matches the lines of the tags. For each tag we create a EXISTS statement, chaining all together and sending them
    to the database.
    If the document (identified by ID and collection) is not in the database, it's added.
    For each tag not present in the database, it is added.

    :param str content: Content of the PubTator file
    :param str collection: Identifier of the collection (e.g., PMC)
    :param str or None tagger: Name of the tagger
    """
    session = Session.get()
    document_match = CONTENT_ID_TIT_ABS.match(content)
    document_id = int(document_match.group(1))
    q_document = session.query(Document).filter_by(id=document_id, collection=collection).exists()
    tags_match = TAG_LINE_NORMAL.findall(content)
    tag_kwargs = [tag_kwargs_from_match(m, collection) for m in tags_match]
    q_tags = [session.query(Tag).filter_by(**kwargs).exists() for kwargs in tag_kwargs]
    results = session.query(q_document, *q_tags).all()[0]
    exists_doc = results[0]
    exists_tags = results[1:]
    if not exists_doc:
        session.add(Document(
            id=document_id,
            collection=collection,
            title=document_match.group(2).strip(),
            abstract=document_match.group(3).strip(),
            date_inserted=datetime.now(),
        ))
    for result, kwargs in zip(exists_tags, tag_kwargs):
        if not result:
            session.add(Tag(**kwargs, tagger=tagger))
    if not all(results):
        session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("collection")
    parser.add_argument("--tagger", help="Name of the tagger", default=None)
    parser.add_argument("--bulk", action="store_true")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    if args.bulk:
        bulk_load(args.input, args.collection, args.tagger)
    else:
        with open(args.input) as f:
            content = f.read()
        load_single(content, args.collection, args.tagger)


if __name__ == "__main__":
    main()
