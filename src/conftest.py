import os
import shutil
from pathlib import Path

from narraint.backend.database import SessionExtended
from nitests.util import tmp_rel_path


def pytest_sessionstart(session):
    # Override global configuration vars
    import narraint.config
    backend_config = Path(narraint.config.GIT_ROOT_DIR) / "src/nitests/config/jsonfiles/backend.json"
    print(f"backend_config: {backend_config}")
    shutil.rmtree(tmp_rel_path(""), ignore_errors=True)
    os.makedirs(tmp_rel_path(""))
    sql_session = SessionExtended.get(backend_config)
