import shutil
import os

from narraint.tools import proj_rel_path

def pytest_sessionstart(session):
    # Override global configuration vars
    import nitests.config.config_mod
    shutil.rmtree(proj_rel_path("nitests/tmp/"))
    os.mkdir(proj_rel_path("nitests/tmp/"))