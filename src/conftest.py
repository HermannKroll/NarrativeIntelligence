import shutil
import os

from narraint.backend.database import Session
from narraint.tools import proj_rel_path
from nitests.util import tmp_rel_path


def pytest_sessionstart(session):
    # Override global configuration vars
    import nitests.config.config_mod
    import narraint.config
    print("backend_config:" + narraint.config.BACKEND_CONFIG)
    shutil.rmtree(tmp_rel_path(""))
    os.mkdir(tmp_rel_path(""))
    session = Session.get()
