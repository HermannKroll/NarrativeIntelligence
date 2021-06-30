from narrant import tools

from narrant import config
from narraint import config as config2
config.BACKEND_CONFIG = tools.proj_rel_path("src/nitests/config/jsonfiles/backend.json")
config2.BACKEND_CONFIG = config.BACKEND_CONFIG
