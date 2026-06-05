from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker, DocumentFragment


class CoverageDocumentRanker(BaseDocumentRanker):
    def __init__(self, corpus: DocumentCorpus, name="CoverageDocumentRanker"):
        super().__init__(name=name, corpus=corpus)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument, fragment: DocumentFragment):
        # find the lowest scored coverage of some subject/object of the fragment's statements
        return min([c.subject.coverage for c in fragment.statements] + [c.object.coverage for c in fragment.statements])
