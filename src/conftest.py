import os
import shutil
from pathlib import Path

from narraint.backend.database import SessionExtended
from nitests.util import tmp_rel_path

from narraint import config as config2
from kgextractiontoolbox import config as config3
from narrant import config


def pytest_sessionstart(session):
    # Override global configuration vars
    import narraint.config
    backend_config = Path(narraint.config.GIT_ROOT_DIR) / "src/nitests/config/jsonfiles/backend.json"

    config.BACKEND_CONFIG = backend_config
    config2.BACKEND_CONFIG = config.BACKEND_CONFIG
    config3.BACKEND_CONFIG = config.BACKEND_CONFIG

    print(f"backend_config: {backend_config}")
    shutil.rmtree(tmp_rel_path(""), ignore_errors=True)
    os.makedirs(tmp_rel_path(""))
    sql_session = SessionExtended.get(backend_config)
