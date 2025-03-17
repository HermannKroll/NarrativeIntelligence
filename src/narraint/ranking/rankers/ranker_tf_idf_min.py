from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker
from narraint.ranking.scoring import score_edge_by_entity_tf_idf


class TfIdfMinDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="TfIdfMinDocumentRanker"):
        super().__init__(name=name)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument,
                               corpus: DocumentCorpus, fragment: list):
        scores = list()
        for spo in fragment:
            scores.append(score_edge_by_entity_tf_idf(spo, corpus=corpus))
        return min(scores)
