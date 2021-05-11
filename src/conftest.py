import shutil
import os

from narraint.backend.database import SessionExtended
from narrant.tools import proj_rel_path
from nitests.util import tmp_rel_path


def pytest_sessionstart(session):
    # Override global configuration vars
    import nitests.config.config_mod
    import narraint.config
    print("backend_config:" + narraint.config.BACKEND_CONFIG)
    shutil.rmtree(tmp_rel_path(""), ignore_errors=True)
    os.makedirs(tmp_rel_path(""))
    session = SessionExtended.get()
