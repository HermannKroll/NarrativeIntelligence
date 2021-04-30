import logging
import os
import tempfile

from narrant.backend.database import Session
from narraint.config import PREPROCESS_CONFIG
from narrant.pubtator.document import TaggedEntity
from narrant.pubtator.extract import collect_ids_from_dir
from narraint.tools import proj_rel_path
from nitests.config.config import TEST_RESOURCES_DIR
import narrant.preprocessing.config as cnf


def create_test_kwargs(in_dir):
    _, mapping_file_id, mapping_id_file = collect_ids_from_dir(in_dir)
    config = cnf.Config(PREPROCESS_CONFIG)
    test_kwargs = dict(collection="testcol", root_dir=make_test_tempdir(), input_dir=in_dir,
                       logger=logging,
                       log_dir=make_test_tempdir(),
                       config=config, mapping_id_file=mapping_id_file, mapping_file_id=mapping_file_id)
    return test_kwargs


def get_test_resource_filepath(filename):
    return resource_rel_path(filename)


def tmp_rel_path(path):
    return proj_rel_path("src/nitests/tmp/" + path)


def resource_rel_path(path):
    return proj_rel_path("src/nitests/resources/" + path)


def make_test_tempdir():
    return tempfile.mkdtemp()


def is_file_content_equal(file_1, file_2):
    with open(file_1) as f1, open(file_2) as f2:
        return f1.read() == f2.read()


def get_tags_from_database(doc_id=None):
    session = Session.get()
    if id is None:
        result = session.execute("SELECT * FROM tag")
    else:
        result = session.execute(f"SELECT * FROM TAG WHERE document_id={doc_id}")
    for row in result:
        yield TaggedEntity((row["document_id"], row["start"], row["end"],
                            row["ent_str"], row["ent_type"], row["ent_id"]))

def clear_database():
    """DANGER! ONLY USE IN TESTS, NOWHERE IN PRODUCTION CODE!"""
    session = Session.get()
    if Session.is_sqlite:
        session.execute("DELETE FROM tag")
        session.execute("DELETE FROM doc_tagged_by")
