import math
from typing import Dict
from sentence_transformers import SentenceTransformer

from narraint.recommender.core import NarrativeCoreExtractor
from narraint.recommender.recommender_config import GRAPH_WEIGHT, BM25_WEIGHT
from narraint.recommender.document import RecommenderDocument


class Recommender:
    """
    Previously called GraphBaseFallbackBM25, now default recommender implementation
    """
    def __init__(self, extractor: NarrativeCoreExtractor):
        self.extractor = extractor
        self.sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

    def recommend_documents_core_overlap(self, doc: RecommenderDocument, docs_from: [RecommenderDocument]) -> [RecommenderDocument]:
        # Compute the cores
        # scores are sorted by their size
        core = self.extractor.extract_narrative_core_from_document(doc)
        if not core:
            return [(d.id, 1.0) for d in docs_from]

        # Core statements are also sorted by their score
        document_ids_scored = {d.id: 0.0 for d in docs_from}
        for candidate in docs_from:
            cand_core = self.extractor.extract_narrative_core_from_document(candidate)
            if cand_core:
                for stmt in core.intersect(cand_core).statements:
                    document_ids_scored[candidate.id] += stmt.score

        # Get the maximum score to normalize the scores
        max_score = max(document_ids_scored.values())
        # Convert to list
        if max_score > 0.0:
            document_ids_scored = [(k, v / max_score) for k, v in document_ids_scored.items()]
        else:
            document_ids_scored = [(k, v) for k, v in document_ids_scored.items()]
        # Sort by score and then doc desc
        document_ids_scored.sort(key=lambda x: (x[1], x[0]), reverse=True)
        # Ensure cutoff
        return document_ids_scored

    @staticmethod
    def normalize_scores(document_ids_scored: Dict[str, float]) -> Dict[str, float]:
        # Get the maximum score to normalize the scores
        max_score = max(document_ids_scored.values())
        # Convert to list
        if max_score > 0.0:
            document_ids_scored = {k: (v / max_score) for k, v in document_ids_scored.items()}
        # Ensure cutoff
        return document_ids_scored


    def recommend_documents_sentence_embedding(self, doc: RecommenderDocument, docs_from: [RecommenderDocument]):
        sentences = [doc.get_text_content(), *[d.get_text_content() for d in docs_from]]

        # create the semantic embeddings using the model
        embeddings = self.sbert_model.encode(sentences)

        # calculate similarities between the doc and the recommended docs (default COSINE-Similarity)
        similarities = self.sbert_model.similarity(embeddings[0], embeddings[1:])

        print(similarities[0])
        assert len(similarities[0]) == len(docs_from)
        return {d.id: s for d, s in zip(docs_from, similarities)}


    def recommend_documents(self, doc: RecommenderDocument, docs_from: [RecommenderDocument]) -> [RecommenderDocument]:
        # first score every document with the implemented graph strategy
        document_ids_scored_graph = self.recommend_documents_core_overlap(doc, docs_from)
        # convert to dictionary
        document_ids_scored_graph = {k: v for k, v in document_ids_scored_graph}
        document_ids_scored_graph = self.normalize_scores(document_ids_scored_graph)

        # then score every document with BM25
        # TODO find an alternative
        # TODO bm25scorer for now disabled - maybe implement sBERT?
        document_ids_scored_bm25 = self.recommend_documents_sentence_embedding(doc, docs_from)
        document_ids_scored_bm25 = self.normalize_scores(document_ids_scored_graph)

        document_ids_scored = {}
        for d, graph_score in document_ids_scored_graph.items():
            document_ids_scored[d] = GRAPH_WEIGHT * graph_score + BM25_WEIGHT * document_ids_scored_bm25[d]

        # Sort by score and then doc desc
        document_ids_scored = sorted([(k, v) for k, v in document_ids_scored.items()],
                                     key=lambda x: (x[1], x[0]), reverse=True)
        # Ensure cutoff
        return document_ids_scored
