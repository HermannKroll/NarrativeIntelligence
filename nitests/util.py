import logging
import os
import tempfile

from narraint.config import PREPROCESS_CONFIG
from narraint.pubtator.extract import collect_ids_from_dir
from narraint.tools import proj_rel_path
from nitests.config.config import TEST_RESOURCES_DIR
import narraint.preprocessing.config as cnf



def create_test_kwargs(in_dir):
    _, mapping_file_id, mapping_id_file = collect_ids_from_dir(in_dir)
    config = cnf.Config(PREPROCESS_CONFIG)
    test_kwargs = dict(collection="testcol", root_dir=make_test_tempdir(), input_dir=in_dir,
                       logger=logging,
                       log_dir=make_test_tempdir(),
                       config=config, mapping_id_file=mapping_id_file, mapping_file_id=mapping_file_id)
    return test_kwargs

def get_test_resource_filepath(filename):
    return os.path.join(TEST_RESOURCES_DIR, filename)


def make_test_tempdir():
    return tempfile.mkdtemp()

def is_file_content_equal(file_1, file_2):
    with open(file_1) as f1, open(file_2) as f2:
        return f1.read() == f2.read()