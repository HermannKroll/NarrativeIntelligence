import os
import tempfile

from narraint import config

TEST_RESOURCES_DIR = os.path.join(config.GIT_ROOT_DIR, 'nitests/resources')


def get_test_resource_filepath(filename):
    return os.path.join(TEST_RESOURCES_DIR, filename)


def make_test_tempdir():
    return tempfile.mkdtemp()
