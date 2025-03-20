from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker, DocumentFragment
from narraint.ranking.scoring import score_edge_by_entity_tf_idf


class TfIdfMinDocumentRanker(BaseDocumentRanker):
    def __init__(self, corpus:DocumentCorpus, name="TfIdfMinDocumentRanker"):
        super().__init__(corpus=corpus, name=name)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument, fragment: DocumentFragment):
        return min(score_edge_by_entity_tf_idf(statement=stmt, corpus=self.corpus) for stmt in fragment.statements)
