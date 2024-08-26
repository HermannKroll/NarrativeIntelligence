import json
import os

from narraint.config import RESOURCE_DIR


class DataSourcesFilter:
    file_path = os.path.join(RESOURCE_DIR, "data_sources.json")
    data_sources = None

    @staticmethod
    def get_available_data_sources():
        if DataSourcesFilter.data_sources is not None:
            return DataSourcesFilter.data_sources

        if not os.path.exists(DataSourcesFilter.file_path):
            raise FileNotFoundError(f"Config file not found: {DataSourcesFilter.file_path}")

        with open(DataSourcesFilter.file_path) as f:
            DataSourcesFilter.data_sources = json.load(f)
        return DataSourcesFilter.data_sources

    @staticmethod
    def get_available_db_collections():
        doc_collections = DataSourcesFilter.get_available_data_sources()
        return {c["collection"] for c in doc_collections}
