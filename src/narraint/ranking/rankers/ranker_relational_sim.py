import itertools

from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.document import AnalyzedNarrativeDocument
from narraint.ranking.query import AnalyzedQuery
from narraint.ranking.rankers.ranker_base import BaseDocumentRanker


class RelationalSimDocumentRanker(BaseDocumentRanker):
    def __init__(self, name="RelationalSimDocumentRanker"):
        super().__init__(name=name)

    @staticmethod
    def get_relational_similarity_scores(doc: AnalyzedNarrativeDocument, corpus: DocumentCorpus, fragment: list):
        scores = list()
        for spo in fragment:

            visited = set()
            for statement in itertools.chain(doc.concept2statement[spo[0]], doc.concept2statement[spo[2]]):
                # iterate over each edge once
                n_spo = (statement.subject_id, statement.relation, statement.object_id)
                if n_spo in visited:
                    continue
                visited.add(n_spo)

                # skip edges between the fragment
                if n_spo[0] == spo[0] and n_spo[2] == spo[2]:
                    continue

                # neighbour edge = edge that is connected to the fragment via subject or object
                if n_spo[0] == spo[0] or n_spo[2] == spo[2]:
                    tf_idf = BaseDocumentRanker.get_tf_idf(statement=n_spo, doc=doc, corpus=corpus)
                    confidence = max(doc.spo2confidences[n_spo])
                    coverage = min(doc.get_concept_coverage(n_spo[0]), doc.get_concept_frequency(n_spo[2]))
                    score = confidence * tf_idf * coverage
                    scores.append(score)

        # we might do not have neighbour edges
        if len(scores) == 0:
            return [0.0]

        return scores

    def rank_document_fragment(self, query: AnalyzedQuery, doc: AnalyzedNarrativeDocument,
                               corpus: DocumentCorpus, fragment: list):

        scores = RelationalSimDocumentRanker.get_relational_similarity_scores(doc, corpus, fragment)
        return sum(scores)
