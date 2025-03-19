from typing import List

from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.corpus import DocumentCorpus


class GraphRank:

    def __init__(self):
        self.corpus = DocumentCorpus()

    def rank_document(self, query_results: List[QueryDocumentResult]) -> List[QueryDocumentResult]:
        collections = set([r.document_collection for r in query_results])
        # we need to rank over each collection speparatly
