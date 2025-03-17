from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker


class ConfidenceDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="ConfidenceDocumentRanker"):
        super().__init__(name=name)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument,
                               corpus: DocumentCorpus, fragment: list):
        scores = list()
        for s, p, o in fragment:
            scores.append(max(doc.spo2confidences[(s, p, o)]))
        return min(scores)
