import itertools

from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker, DocumentFragment
from narraint.ranking.scoring import score_edge_by_tfidf_coverage_confidence


class RelationalSimDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="RelationalSimDocumentRanker"):
        super().__init__(name=name)

    @staticmethod
    def get_relational_similarity_scores(doc: IndexedDocument, corpus: DocumentCorpus, fragment: DocumentFragment):
        scores = list()
        for f_statement in fragment.statements:
            visited = set()
            subject_key = f_statement.subject.get_unique_key()
            object_key = f_statement.object.get_unique_key()
            for neighbor_stmt in itertools.chain(doc.entity_key2statements[subject_key], doc.entity_key2statements[object_key]):
                # iterate over each edge once
                n_key = neighbor_stmt.get_unique_key()
                if n_key in visited:
                    continue
                visited.add(n_key)

                # skip edges between the fragment
                if f_statement.has_equal_entities(neighbor_stmt):
                    continue

                # neighbour edge = edge that is connected to the fragment via subject or object
                if f_statement.has_overlapping_entities(neighbor_stmt):
                    scores.append(score_edge_by_tfidf_coverage_confidence(statement=neighbor_stmt, corpus=corpus))

        # we might do not have neighbour edges
        if len(scores) == 0:
            return [0.0]

        return scores

    def rank_document_fragment(self, query: AnalyzedQuery, doc: IndexedDocument,
                               corpus: DocumentCorpus, fragment: DocumentFragment):
        scores = RelationalSimDocumentRanker.get_relational_similarity_scores(doc, corpus, fragment)
        return sum(scores)
