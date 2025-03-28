from typing import List

from narraint.backend.database import SessionExtended
from narraint.queryengine.query import GraphQuery
from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.graph_fragment import GraphFragmentExtractor
from narraint.ranking.indexed_document import retrieve_indexed_documents_from_database_small, get_unique_document_key
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_confidence import ConfidenceDocumentRanker
from narraint.ranking.rankers.ranker_coverage import CoverageDocumentRanker
from narraint.ranking.rankers.ranker_relational_sim import RelationalSimDocumentRanker
from narraint.ranking.rankers.ranker_tf_idf_min import TfIdfMinDocumentRanker


class GraphRank:

    def __init__(self):
        self.corpus = DocumentCorpus()
        self.rankers = [ConfidenceDocumentRanker(self.corpus), CoverageDocumentRanker(self.corpus),
                        RelationalSimDocumentRanker(self.corpus), TfIdfMinDocumentRanker(self.corpus)]
        self.weights = [0.25, 0.25, 0.25, 0.25]

        assert len(self.weights) == len(self.rankers)
        assert sum(self.weights) == 1.0

    def rank_document(self, graph_query: GraphQuery, query_results: List[QueryDocumentResult]) -> List[QueryDocumentResult]:
        session = SessionExtended.get()
        # we need to retrieve data for each collection separately
        collections = {r.document_collection for r in query_results}
        indexed_docs = []
        for collection in collections:
            dids = {r.document_id for r in query_results if r.document_collection == collection}
            indexed_docs.extend(retrieve_indexed_documents_from_database_small(session, document_ids=dids,
                                                                               document_collection=collection))

        # remove opened session
        session.remove()

        # analyze query
        query = AnalyzedQuery(graph_query)

        # Compute the fragment matches between a document and the query
        # a "fragment" explains the match, i.e. it selects the scored statements that match the query
        fragments = [GraphFragmentExtractor.matches(query, doc) for doc in indexed_docs]

        # next compute the document score
        ranker2scores = {}
        for ranker in self.rankers:
            ranker2scores[ranker.name] = ranker.rank_documents(query, indexed_docs, fragments)

        for result in query_results:
            result.score = sum(self.weights[i] * ranker2scores[r.name][get_unique_document_key(result.document_id,
                                                                                               result.document_collection)]
                               for i, r in enumerate(self.rankers))

        # sort and return the documents
        return sorted(query_results, key=lambda x: (x.score, x.document_id), reverse=True)
