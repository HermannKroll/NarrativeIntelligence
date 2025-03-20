from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery


class GraphFragment:

    @staticmethod
    def matches(query: AnalyzedQuery, document: IndexedDocument):
        """
        Computes all distinct subgraph isomorphism between the query q and the document graph of d.
        Each subgraph isomorphism maps a part of the document graph to the query.
        Note that if q asks for two statements, each isomorphism must map two document edges to the
        corresponding query graph edges.

        Given two statements in a query:
        stmt1 maps to which edges of the document graph g? -> given by query engine through predication ids
        stmt2 maps to which edges of the document graph g? -> given by query engine through predication ids
        Cross product between all combinations
        """
        # Todo: Implementation missing
        raise NotImplementedError
