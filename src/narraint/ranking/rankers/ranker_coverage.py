from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker, DocumentFragment


class ConceptCoverageDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="ConceptCoverageDocumentRanker"):
        super().__init__(name=name)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument,
                               corpus: DocumentCorpus, fragment: DocumentFragment):
        # find the lowest scored coverage of some subject/object of the fragment's statements
        return min([c.subject.coverage for c in fragment.statements] + [c.object.coverage for c in fragment.statements])
