from pathlib import Path

from narraint import config as config2
from kgextractiontoolbox import config as config3
from narrant import config


import narraint.config

backend_config = Path(narraint.config.GIT_ROOT_DIR) / "src/nitests/config/jsonfiles/backend.json"

config.BACKEND_CONFIG = backend_config
config2.BACKEND_CONFIG = config.BACKEND_CONFIG
config3.BACKEND_CONFIG = config.BACKEND_CONFIG
