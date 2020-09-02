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


class OpenIESearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'OpenIE'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        query_fact_patterns, _ = convert_query_text_to_fact_patterns(query)
        precision, recall, len_doc_ids, len_ids_in_sample, len_correct = perform_evaluation(self.query_engine,
                                                                                            query_fact_patterns,
                                                                                            document_collection,
                                                                                            OPENIE_EXTRACTION,
                                                                                            ids_correct,
                                                                                            id_sample=ids_sample,
                                                                                            do_expansion=True)
        return precision, recall, compute_f_measure(precision, recall)


class PathIESearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'PathIE'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        query_fact_patterns, _ = convert_query_text_to_fact_patterns(query)
        precision, recall, len_doc_ids, len_ids_in_sample, len_correct = perform_evaluation(self.query_engine,
                                                                                            query_fact_patterns,
                                                                                            document_collection,
                                                                                            PATHIE_EXTRACTION,
                                                                                            ids_correct,
                                                                                            id_sample=ids_sample,
                                                                                            do_expansion=True)
        return precision, recall, compute_f_measure(precision, recall)
