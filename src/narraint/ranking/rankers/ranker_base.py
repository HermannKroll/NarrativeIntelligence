from abc import abstractmethod
from typing import List, Tuple

from narraint.ranking.corpus import DocumentCorpus, PREDICATE_TO_SCORE
from narraint.ranking.document import AnalyzedNarrativeDocument
from narraint.ranking.query import AnalyzedQuery


class ScoredDocumentFragment:

    def __init__(self, score: float, translation_score: float):
        self.score = score
        self.translation_score = translation_score
        assert 0.0 <= self.translation_score <= 1.0

    def __str__(self):
        return f'Score: {self.score} / Translation Score: {self.translation_score}'

    def __repr__(self):
        return self.__str__()


class BaseDocumentRanker:
    @abstractmethod
    def __init__(self, name):
        self.name = name

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument],
                       corpus: DocumentCorpus, fragments: list) -> List[Tuple[str, float]]:

        max_fragment_score = 0.0
        scored_document_fragments = []
        for doc, d_fragments in zip(narrative_documents, fragments):
            scored_fragments = self.rank_document(query, doc, corpus, d_fragments)
            # find the maximum overall document score
            max_fragment_score = max(max_fragment_score, max(sf.score for sf in scored_fragments))

            scored_document_fragments.append(scored_fragments)

        # next normalize all document scores by the maximum score
        # and compute the final document score
        results = list()
        assert 0.0 <= max_fragment_score
        for doc, scored_fragments in zip(narrative_documents, scored_document_fragments):
            doc_fragment_scores = []
            for scored_fragment in scored_fragments:
                # normalize the fragment score * translation score
                if max_fragment_score > 0.0:
                    d_fragment_score = (scored_fragment.score / max_fragment_score) * scored_fragment.translation_score
                else:
                    d_fragment_score = scored_fragment.score * scored_fragment.translation_score

                doc_fragment_scores.append(d_fragment_score)

            # take the maximum (best scored fragment) as the score for this document
            score = max(doc_fragment_scores)

            # check that the score is between 0.0 and 1.0
            assert 0.0 <= score <= 1.0
            results.append((doc.document_id_source, score))

        # Sort documents by their score and then their id
        results.sort(key=lambda x: (x[1], x[0]), reverse=True)
        return results

    def rank_document(self, query: AnalyzedQuery, doc: AnalyzedNarrativeDocument,
                      corpus: DocumentCorpus, fragments: list) -> List[ScoredDocumentFragment]:
        scores = list()
        if len(fragments) == 0:
            raise ValueError("No fragments")
        for fragment in fragments:
            scores.append(ScoredDocumentFragment(self.rank_document_fragment(query, doc, corpus, fragment),
                                                 BaseDocumentRanker.get_fragment_translation_score(fragment,
                                                                                                   query)))
        return scores

    @abstractmethod
    def rank_document_fragment(self, query: AnalyzedQuery, doc: AnalyzedNarrativeDocument, corpus: DocumentCorpus,
                               fragment: list):
        raise NotImplementedError("rank_document_fragment is not implemented")

    @staticmethod
    def get_tf_idf(statement: tuple, doc: AnalyzedNarrativeDocument, corpus: DocumentCorpus):
        tf_s = doc.concept2frequency[statement[0]] / doc.max_concept_frequency
        tf_o = doc.concept2frequency[statement[2]] / doc.max_concept_frequency
        idf_s = corpus.get_concept_ifd_score(statement[0])
        idf_o = corpus.get_concept_ifd_score(statement[2])

        return ((tf_s * idf_s) + (tf_o * idf_o)) * PREDICATE_TO_SCORE[statement[1]]

    @staticmethod
    def get_concept_tf_idf(entity_id: str, doc: AnalyzedNarrativeDocument, corpus: DocumentCorpus):
        tf = doc.concept2frequency[entity_id] / doc.max_concept_frequency
        idf = corpus.get_concept_ifd_score(entity_id)
        return tf * idf

    @staticmethod
    def get_fragment_translation_score(fragment: List[tuple], query: AnalyzedQuery):
        # the fragment is only as good as it weakest translation
        scores = []
        for statement in fragment:
            scores.append(query.concept2score[statement[0]])
            scores.append(query.concept2score[statement[2]])

        min_score = min(scores)
        assert 0.0 <= min_score <= 1.0
        return min_score
