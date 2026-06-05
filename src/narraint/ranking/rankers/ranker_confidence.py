from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker, DocumentFragment


class ConfidenceDocumentRanker(BaseDocumentRanker):
    def __init__(self, corpus: DocumentCorpus, name="ConfidenceDocumentRanker"):
        super().__init__(name=name, corpus=corpus)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument, fragment: DocumentFragment):
        return min([s.confidence for s in fragment.statements])
