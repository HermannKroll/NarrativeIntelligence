from typing import List

from narraint.analysis.documentranking.ranker import AbstractDocumentRanker, AnalyzedQuery, AnalyzedNarrativeDocument


class BM25Ranker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="BM25Ranker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        return list([d.document.id for d in narrative_documents])


class BM25R3Ranker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="BM25R3Ranker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        return list([d.document.id for d in narrative_documents])
