import argparse
import gc
import logging
import os
import sys
from datetime import datetime

from narraint.backend.database import Session
from narraint.backend.models import Document, Tag, ProcessedFor
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS, TAG_LINE_NORMAL
from narraint.tools import count_lines

MAX_BULK_SIZE = 50000


def get_ids_contents_tags(pubtator_content):
    m_tags = TAG_LINE_NORMAL.findall(pubtator_content)
    m_documents = CONTENT_ID_TIT_ABS.findall(pubtator_content)
    document_ids = set(int(m[0]) for m in m_documents)
    documents = set((int(m[0]), m[1].strip(), m[2].strip()) for m in m_documents)
    tags = set((int(m[0]), int(m[1]), int(m[2]), m[3].strip(), m[4].strip(), m[5].strip()) for m in m_tags)
    return document_ids, documents, tags


# TODO: Add processed_by relation
# TODO: Take schema change into account
def bulk_load(path, collection, max_bulk=MAX_BULK_SIZE, tagger=None):
    """
    Bulk load a file in PubTator Format or a directory of PubTator files into the database.

    1. Read file memory-friendly and create sets for document ids, documents and tags
    2. Retrieve existing documents and tags (lock table)
    3. Prepare statements (check if documents/tags are) already in database)
    4. Commit transaction

    :param max_bulk: Number of tuples after which an insert is performed
    :param str or None tagger: Name of the used tagger
    :param str collection: Identifier of the collection (e.g., PMC)
    :param str path: Path to file or directory
    :return:
    """
    sys.stdout.write("Reading files ... 0.0 %")
    sys.stdout.flush()
    document_ids = set()
    documents = set()
    tags = set()
    if os.path.isdir(path):
        files = [os.path.join(path, fn) for fn in os.listdir(path) if not fn.startswith(".") and fn.endswith(".txt")]
        for idx, fn in enumerate(files):
            with open(fn) as f:
                d_ids, d_contents, d_tags = get_ids_contents_tags(f.read())
                document_ids.update(d_ids)
                documents.update(d_contents)
                tags.update(d_tags)
            sys.stdout.write("\rReading files ... {:.1f} %".format((idx + 1.0) / len(files) * 100.0))
            sys.stdout.flush()
    else:
        content = ""
        line_count = count_lines(path)
        last_percentage = 0
        with open(path) as f:
            for idx, line in enumerate(f):
                if line.strip():
                    content += line
                else:
                    d_ids, d_contents, d_tags = get_ids_contents_tags(content)
                    document_ids.update(d_ids)
                    documents.update(d_contents)
                    tags.update(d_tags)
                    content = ""
                if int((idx + 1.0) / line_count * 1000.0) > last_percentage:
                    last_percentage = int((idx + 1.0) / line_count * 1000.0)
                    sys.stdout.write("\rReading files ... {:.1f} %".format(last_percentage / 10.0))
                    sys.stdout.flush()
    sys.stdout.write(" {} documents and {} tags\n".format(len(documents), len(tags)))

    # Retrieving existing documents
    sys.stdout.write("Retrieving ... ")
    sys.stdout.flush()
    Session.lock_tables("document", "tag")
    session = Session.get()
    db_document_ids = set(
        x[0] for x in session.query(Document).filter(Document.collection == collection).values(Document.id))
    db_tags = set(session.query(Tag).filter(Tag.document_collection == collection).values(
        Tag.document_id, Tag.start, Tag.end, Tag.ent_str, Tag.ent_type, Tag.ent_id,
    ))
    sys.stdout.write("\rRetrieving ... {} documents and {} tags\n".format(len(db_document_ids), len(db_tags)))
    sys.stdout.flush()

    # Preparing ORM objects
    sys.stdout.write("Adding documents ... 0.0 %")
    sys.stdout.flush()
    n_docs = len(documents)
    start = datetime.now()
    objects = []
    for idx, doc in enumerate(documents):
        if doc[0] not in db_document_ids:
            objects.append(Document(
                id=doc[0],
                collection=collection,
                title=doc[1],
                abstract=doc[2],
            ))
        if len(objects) > max_bulk:
            session.bulk_save_objects(objects)
            objects = []
            gc.collect()
        sys.stdout.write("\rAdding documents ... {:0.1f} %".format(int((idx + 1.0) / n_docs * 100.0)))
        sys.stdout.flush()

    # TODO: Take schema change into account
    sys.stdout.write("\nAdding tags ... 0.0 %")
    sys.stdout.flush()
    n_tags = len(tags)
    for idx, tag in enumerate(tags):
        if tag not in db_tags and tag[5].strip():
            objects.append(Tag(
                start=tag[1],
                end=tag[2],
                ent_type=tag[4],
                ent_str=tag[3],
                ent_id=tag[5],
                document_id=tag[0],
                document_collection=collection,
                tagger=tagger,
            ))
        sys.stdout.write("\rAdding tags ... {:0.1f} %".format((idx + 1.0) / n_tags * 100.0))
        sys.stdout.flush()
        if len(objects) > max_bulk:
            session.bulk_save_objects(objects)
            objects = []
            gc.collect()

    sys.stdout.write("\nDone in {}\nCommitting ...".format(datetime.now() - start))
    sys.stdout.flush()

    # Committing to database
    start = datetime.now()
    session.bulk_save_objects(objects)
    session.commit()
    sys.stdout.write(" done in {}\n".format(datetime.now() - start))
    sys.stdout.flush()


# TODO: Move to backend.utils (?) because model parameters are used
def tag_kwargs_from_match(m, collection):
    return dict(
        ent_type=m[4],
        start=int(m[1]),
        end=int(m[2]),
        ent_id=m[5],
        ent_str=m[3],
        document_id=int(m[0]),
        document_collection=collection,
    )


# TODO: Take schema change into account
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
    Session.lock_tables("document", "tag", "processed_for")
    session = Session.get()
    document_match = CONTENT_ID_TIT_ABS.match(content)
    document_id = int(document_match.group(1))

    if not session.query(session.query(Document).filter_by(id=document_id, collection=collection).exists()).scalar():
        session.add(Document(
            id=document_id,
            collection=collection,
            title=document_match.group(2).strip(),
            abstract=document_match.group(3).strip(),
        ))
    else:
        print("Document already exists.")

    # TODO: Take schema change into account
    tags_match = TAG_LINE_NORMAL.findall(content)
    tag_kwargs = [tag_kwargs_from_match(m, collection) for m in tags_match if m[5].strip()]
    q_tags = [session.query(Tag).filter_by(**kwargs).exists() for kwargs in tag_kwargs]
    if q_tags:
        results = session.query(*q_tags).all()[0]
        for result, kwargs in zip(results, tag_kwargs):
            if not result:
                session.add(Tag(**kwargs, tagger=tagger))

    # TODO: Take schema change into account
    ent_types = set(kwargs["ent_type"] for kwargs in tag_kwargs)
    for ent_type in ent_types:
        query = session.query(ProcessedFor).filter_by(
            document_id=document_id, document_collection=collection, ent_type=ent_type,
        ).exists()
        if not session.query(query).scalar():
            session.add(ProcessedFor(
                document_id=document_id,
                document_collection=collection,
                ent_type=ent_type,
            ))

    session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("collection")
    parser.add_argument("--tagger", help="Name of the tagger", default=None)
    parser.add_argument("--bulk", action="store_true")
    parser.add_argument("--log", action="store_true")
    parser.add_argument("--max-bulk", type=int, default=MAX_BULK_SIZE, help="Max bulk size")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    if args.bulk:
        bulk_load(args.input, args.collection, tagger=args.tagger, max_bulk=args.max_bulk)
    else:
        with open(args.input) as f:
            content = f.read()
        load_single(content, args.collection, args.tagger)


if __name__ == "__main__":
    main()
