from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import ScoredDocumentEntity, ScoredDocumentStatement

PREDICATE_TO_SCORE = {
    "associated": 0.25,
    "administered": 1.0,
    "compares": 1.0,
    "decreases": 0.5,
    "induces": 1.0,
    "interacts": 0.5,
    "inhibits": 1.0,
    "metabolises": 1.0,
    "treats": 1.0,
    "method": 1.0
}


def score_edge_by_tf_and_concept_idf(statement: ScoredDocumentStatement,  corpus: DocumentCorpus):
    tf_s = statement.subject.tf_normalized
    tf_o = statement.object.tf_normalized
    idf_s = corpus.get_concept_ifd_score(statement.subject)
    idf_o = corpus.get_concept_ifd_score(statement.object)

    tfidf = PREDICATE_TO_SCORE[statement.relation] * (0.5 * ((tf_s * idf_s) + (tf_o * idf_o)))

    coverage = min(statement.subject.coverage, statement.object.coverage)

    assert 0.0 <= tfidf <= 1.0
    assert 0.0 <= coverage <= 1.0
    return coverage * statement.confidence * tfidf


def score_concept_by_tf_idf_and_coverage(entity: ScoredDocumentEntity, corpus: DocumentCorpus):
    return entity.coverage * (entity.tf_normalized * corpus.get_concept_ifd_score(entity))
