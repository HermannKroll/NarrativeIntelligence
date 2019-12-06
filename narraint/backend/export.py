import argparse
import logging
import os
import re
import sys
from datetime import datetime

from narraint.backend.database import Session
from narraint.backend.models import Document, Tag

PUBTATOR_REGEX = re.compile(r"(\d+)\|t\|(.*?)\n\d+\|a\|(.*?)\n")
TAG_REGEX = re.compile(r"(\d+)\t(\d+)\t(\d+)\t(.*?)\t(.*?)\t(.*?)\n")
PUBTATOR_CONTENT_REGEX = re.compile(r"\d+.*?\n\n", re.DOTALL)


def bulk_load(path, collection, tagger=None):
    """
    Bulk load a file in PubTator Format or a directory of PubTator files into the database.

    :param str or None tagger: Name of the used tagger
    :param str collection: Identifier of the collection (e.g., PMC)
    :param str path: Path to file or directory
    :return:
    """
    sys.stdout.write("Reading file ...")
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
        content_list = PUBTATOR_CONTENT_REGEX.findall(content)
    sys.stdout.write(" done\n")
    sys.stdout.write("Processing {} documents ... 0.0 %".format(len(content_list)))
    sys.stdout.flush()
    start = datetime.now()
    for idx, content in enumerate(content_list):
        load_single(content, collection, tagger)
        sys.stdout.write("\rProcessing {} documents ... {:0.1f} %".format(
            len(content_list),
            (idx + 1.0) / len(content_list) * 100.0))
        sys.stdout.flush()
    sys.stdout.write(" in {}\n".format(datetime.now() - start))


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
    document_match = PUBTATOR_REGEX.match(content)
    document_id = int(document_match.group(1))
    q_document = session.query(Document).filter_by(id=document_id, collection=collection).exists()
    tags_match = TAG_REGEX.finditer(content)
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


# def add_pubtator_lines(lines, collection, tagger_name=None, tagger_version=None):
#     """
#     Function takes a series of lines of a PubTator file and creates Document and Tag objects in the database.
#
#     At first, all existing documents and tags are fetched for faster processing.
#
#     This function implements a state machine. It starts with the title line and creates a new Document object if
#     no corresponding document exists. Otherwise it uses the previously fetched document.
#
#     :param lines: List of lines (without \n at end)
#     :param collection: Collection ID (e.g., PMC)
#     :param tagger_name: Name of used tagger
#     :param tagger_version: Version of used tagger
#     """
#     session = Session.get()
#     # Create index
#     sys.stdout.write("Creating index ...")
#     sys.stdout.flush()
#     existing_docs = session.query(Document).filter_by(collection=collection).all()
#     existing_doc_by_id = {d.id: d for d in existing_docs}
#     existing_pairs = session.query(Document, Tag).filter_by(collection=collection).join(Tag).all()
#     existing_tags_by_doc_id = dict()
#     for pair in existing_pairs:
#         doc_id = pair[0].id
#         if pair[0].id not in existing_tags_by_doc_id:
#             existing_tags_by_doc_id[doc_id] = set()
#         existing_tags_by_doc_id[doc_id].add(pair[1])
#     sys.stdout.write(" done\n")
#     sys.stdout.flush()
#     # Parse lines
#     document_count = 0
#     tag_count = 0
#     session_needs_commit = False
#     current_doc = None
#     total_count = len(lines)
#     current_count = 0
#     last_percentage = 0
#     datetime_start = datetime.now()
#     for line in lines:
#         if re.match(r"\d+\|t\|", line):  # Title Line
#             did = int(line[:line.index("|")])
#             title = line[line.index("|t|") + 3:]
#             if did in existing_doc_by_id:
#                 current_doc = existing_doc_by_id[did]
#             else:
#                 current_doc = Document(id=did, collection=collection, title=title, date_inserted=datetime.now())
#         elif re.match(r"\d+\|a\|", line):  # Abstract line
#             if current_doc.abstract is None:
#                 abstract = line[line.index("|a|") + 3:]
#                 current_doc.abstract = abstract
#                 session.add(current_doc)
#                 document_count += 1
#                 session_needs_commit = True
#         elif line.count("\t") == 5:  # Tag line
#             elements = line.split("\t")
#             start = int(elements[1])
#             end = int(elements[2])
#             ent_str = elements[3]
#             ent_type = elements[4]
#             ent_id = elements[5]
#             tag = Tag(start=start, end=end, type=ent_type, ent_str=ent_str, ent_id=ent_id, tagger_name=tagger_name,
#                       tagger_version=tagger_version, document_id=current_doc.id,
#                       document_collection=current_doc.collection)
#             if current_doc.id not in existing_tags_by_doc_id or tag not in existing_tags_by_doc_id[current_doc.id]:
#                 session.add(tag)
#                 tag_count += 1
#                 session_needs_commit = True
#         elif line == "":  # Empty line
#             if session_needs_commit:
#                 session.commit()
#                 session_needs_commit = False
#             current_doc = None
#         # Output
#         if int(current_count / total_count * 100.0) > last_percentage:
#             last_percentage = int(current_count / total_count * 100.0)
#             sys.stdout.write("\rLoading data ... {} %".format(last_percentage))
#             sys.stdout.flush()
#         current_count += 1
#     sys.stdout.write("\rLoading data ... added {} documents and {} tags in {}\n".format(
#         document_count, tag_count, datetime.now() - datetime_start))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("collection")
    parser.add_argument("--tagger-name", help="Name of the tagger", default=None)
    parser.add_argument("--tagger-version", help="Version of the tagger", default=None)
    parser.add_argument("--bulk", action="store_true")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    if args.bulk:
        bulk_load(args.input, args.collection, args.tagger_name, args.tagger_version)
    else:
        with open(args.input) as f:
            content = f.read()
        load_single(content, args.collection, args.tagger_name, args.tagger_version)


if __name__ == "__main__":
    main()
