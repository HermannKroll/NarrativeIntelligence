import json
import os

from narraint.config import RESOURCE_DIR
from narraint.queryengine.result import QueryDocumentResult


class ClassificationFilter:
    file_path = os.path.join(RESOURCE_DIR, "classifications.json")
    classifications = None

    @staticmethod
    def get_available_classifications():
        if ClassificationFilter.classifications is not None:
            return ClassificationFilter.classifications

        if not os.path.exists(ClassificationFilter.file_path):
            raise FileNotFoundError(f"Config file not found: {ClassificationFilter.file_path}")

        with open(ClassificationFilter.file_path) as f:
            ClassificationFilter.classifications = json.load(f)
        return ClassificationFilter.classifications

    @staticmethod
    def has_document_classes(d: QueryDocumentResult, document_classes: [str]):
        # No classes required
        if not document_classes:
            return True
        # Classes required but document does not have any
        if not d.document_classes:
            return False
        # Check whether required classes are assigned to the document
        for dc in document_classes:
            if dc not in d.document_classes:
                return False
        return True

    @staticmethod
    def filter_documents(results: [QueryDocumentResult], document_classes: [str]):
        return list([r for r in results if ClassificationFilter.has_document_classes(r, document_classes)])


