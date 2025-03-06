from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.document import AnalyzedNarrativeDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker


class TfIdfMinDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="TfIdfMinDocumentRanker"):
        super().__init__(name=name)

    def rank_document_fragment(self, query: AnalyzedQuery, doc: AnalyzedNarrativeDocument,
                               corpus: DocumentCorpus, fragment: list):
        scores = list()
        for spo in fragment:
            scores.append(BaseDocumentRanker.get_tf_idf(statement=spo, doc=doc, corpus=corpus))
        return min(scores)
