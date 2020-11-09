import os

from narraint import config

TEST_RESOURCES_DIR = os.path.join(config.CODE_DIR, 'tests/resources')


def get_test_resource_filepath(filename):
    return os.path.join(TEST_RESOURCES_DIR, filename)