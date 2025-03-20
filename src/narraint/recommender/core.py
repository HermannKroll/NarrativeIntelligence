from typing import List

from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument, ScoredDocumentStatement, ScoredDocumentEntity
from narraint.ranking.scoring import score_edge_by_tfidf_coverage_confidence, score_concept_by_tf_idf_and_coverage
from narraint.recommender.recommender_config import CONCEPT_MAX_SUPPORT


class NarrativeEntityCore:

    def __init__(self, entities: List[ScoredDocumentEntity]):
        self.entities = entities


class NarrativeCore:

    def __init__(self, statements: List[ScoredDocumentStatement]):
        self.statements = statements
        self.statements.sort(key=lambda x: x.score, reverse=True)
        self.size = len(statements)
        self.graph = {(s.subject.get_unique_key(), s.relation, s.object.get_unique_key()) for s in self.statements}

    def contains_statement(self, spo) -> bool:
        return spo in self.graph

    def intersect(self, other):
        if not isinstance(other, NarrativeCore):
            return None

        statements = []
        for a in self.statements:
            found = False
            for b in other.statements:
                if a.has_equal_entities(b):
                    found = True
                    break
            if found:
                statements.append(a)
        return NarrativeCore(statements)


class NarrativeCoreExtractor:

    def __init__(self, corpus: DocumentCorpus):
        self.corpus = corpus

    def extract_concept_core(self, document: IndexedDocument) -> NarrativeEntityCore:
        if not document.scored_entities:
            return None

        scored_concepts: [ScoredDocumentEntity] = []
        for scored_entity in document.scored_entities:
            score = score_concept_by_tf_idf_and_coverage(scored_entity, self.corpus)
            support = self.corpus.get_entity_support(scored_entity)
            scored_entity.set_score(score)
            if support <= CONCEPT_MAX_SUPPORT:
                scored_concepts.append(scored_entity)

        # sort remaining ones by score
        scored_concepts.sort(key=lambda x: x.score, reverse=True)

        return NarrativeEntityCore(scored_concepts)

    def extract_narrative_core_from_document(self, document: IndexedDocument) -> NarrativeCore:
        if not document.extracted_statements:
            return None

        filtered_statements: [ScoredDocumentStatement] = []
        for statement in document.scored_statements:
            s_score = score_edge_by_tfidf_coverage_confidence(statement, self.corpus)
            statement.set_score(s_score)
            filtered_statements.append(statement)

        if not filtered_statements:
            return None

        # sort filtered statements by score
        filtered_statements.sort(key=lambda x: x.score, reverse=True)

        core_node_pairs = set()
        # The following algorithm will be design select the highest scored edges between two
        # nodes because filtered statements are sorted by their score desc
        # for connected_nodes, size in connected_components:
        core_statements = []
        for statement, _ in filtered_statements:
            # add only the strongest edge between two nodes (could be caused by multiple extractions)
            so = (statement.subject.get_unique_key(), statement.object.get_unique_key())
            os = (statement.object.get_unique_key(), statement.subject.get_unique_key())
            # Check whether we already added an edge between s and o or o and s
            if so in core_node_pairs or os in core_node_pairs:
                continue

            # if statement.subject_id in connected_nodes and statement.object_id in connected_nodes:
            core_statements.append(statement)
            core_node_pairs.add(so)

        core = NarrativeCore(core_statements)
        return core
