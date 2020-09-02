import os

from narraint.analysis.cikm2020.helper import perform_evaluation
from narraint.extraction.versions import OPENIE_EXTRACTION, PATHIE_EXTRACTION
from narraint.pubtator.document import TaggedDocument
from narraint.frontend.ui.views import convert_query_text_to_fact_patterns


def compute_f_measure(precision, recall):
    if precision > 0.0 and recall > 0.0:
        return 2 * (precision * recall) / (precision + recall)
    return 0.0


class SearchStrategy:

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        pass


class TextSearchStrategy(SearchStrategy):

    def __init__(self, document_dir: str):
        self.document_dir = document_dir

    def get_document_content(self, document_id: int, document_collection: str):
        doc_path = os.path.join(self.document_dir, '{}_{}.txt'.format(document_collection, document_id))
        with open(doc_path, 'r') as f:
            return TaggedDocument(f.read())


class DBSearchStrategy(SearchStrategy):

    def __init__(self, query_engine):
        self.query_engine = query_engine

    def query_ie_database(self, query, document_collection, extraction_type, ids_sample, ids_correct):
        query_fact_patterns, _ = convert_query_text_to_fact_patterns(query)
        query_results = self.query_engine.process_query_with_expansion(query_fact_patterns, document_collection,
                                                                       extraction_type, query)
        doc_ids = set([q_r.document_id for q_r in query_results])

        if ids_sample:
            doc_hits = doc_ids.intersection(ids_sample)
        else:
            doc_hits = doc_ids
        doc_ids_correct = doc_hits.intersection(ids_correct)
        len_hits = len(doc_hits)
        len_correct = len(doc_ids_correct)
        if doc_ids_correct:
            precision = len_correct / len_hits
            recall = len_correct / len(ids_correct)
        else:
            precision = 0.0
            recall = 0.0
        return precision, recall, compute_f_measure(precision, recall)


class OpenIESearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'OpenIE'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):

        return self.query_ie_database(query, document_collection, OPENIE_EXTRACTION, ids_sample, ids_correct)


class PathIESearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'PathIE'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        return self.query_ie_database(query, document_collection, PATHIE_EXTRACTION, ids_sample, ids_correct)

