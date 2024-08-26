import json
import os

from narraint.config import RESOURCE_DIR


class DataSourcesFilter:
    file_path = os.path.join(RESOURCE_DIR, "data_sources.json")

    @staticmethod
    def get_available_data_sources():
        if not os.path.exists(DataSourcesFilter.file_path):
            raise FileNotFoundError(f"Config file not found: {DataSourcesFilter.file_path}")

        with open(DataSourcesFilter.file_path) as f:
            doc_collections = json.load(f)
        return doc_collections
