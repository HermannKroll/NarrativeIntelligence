from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.document import AnalyzedNarrativeDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker


class ConceptCoverageDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="ConceptCoverageDocumentRanker"):
        super().__init__(name=name)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: AnalyzedNarrativeDocument,
                               corpus: DocumentCorpus, fragment: list):
        concepts = set()
        for s, p, o in fragment:
            concepts.add(s)
            concepts.add(o)

        scores = [doc.get_concept_coverage(c) for c in concepts]
        return min(scores)
