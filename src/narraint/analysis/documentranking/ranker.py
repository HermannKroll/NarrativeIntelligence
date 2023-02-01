import itertools
from typing import List

import networkx
import nltk

from kgextractiontoolbox.document.document import TaggedEntity
from narraint.analysis.querytranslation.data_graph import Query, DataGraph
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.backend.database import SessionExtended
from narraint.backend.retrieve import retrieve_narrative_documents_from_database
from narraint.document.narrative_document import NarrativeDocument
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entity.entityresolver import GeneResolver
from narrant.preprocessing.enttypes import GENE

stopwords = set(nltk.corpus.stopwords.words('english'))
trans_map = {p: ' ' for p in '[]()?!'}  # PUNCTUATION}
translator = str.maketrans(trans_map)


class AnalyzedQuery:

    def __init__(self, keyword_query):
        self.keyword_query_org = keyword_query
        keyword_query = keyword_query.lower().strip()
        keyword_query = keyword_query.translate(translator)
        possible_keywords = keyword_query.split(' ')
        self.keyword_query = keyword_query
        self.keywords = list([k for k in possible_keywords if k and k not in stopwords])
        self.concepts = set()
        self.tagger = EntityTagger.instance()
        self.__greedy_find_concepts_in_keywords()

    def __greedy_find_concepts_in_keywords(self):

        # perform a backward search
        for j in range(0, len(self.keywords), 1):
            keywords_iteration = self.keywords[j:]
            for i in range(len(keywords_iteration), 0, -1):
                current_part = ' '.join([k for k in keywords_iteration])
          #      print(current_part)
                try:
                    entities_in_part = self.tagger.tag_entity(current_part, expand_search_by_prefix=True)
                    self.concepts.update({e.entity_id for e in entities_in_part})
                    self.concepts.update({e.entity_type for e in entities_in_part})
                except KeyError:
                    pass
        # Perform a forward search
        for j in range(1, len(self.keywords) + 1, 1):
            current_part = ' '.join([k for k in self.keywords[:j]])
       #     print(current_part)
            try:
                entities_in_part = self.tagger.tag_entity(current_part, expand_search_by_prefix=True)
                self.concepts.update({e.entity_id for e in entities_in_part})
                self.concepts.update({e.entity_type for e in entities_in_part})
            except KeyError:
                pass

    def to_dict(self):
        return {"keywords": str(self.keywords),
                "concepts": str(self.concepts)}


class AnalyzedNarrativeDocument:

    def __init__(self, doc: NarrativeDocument):
        self.document = doc
        self.concept_ids = set([t.ent_id for t in doc.tags])
        self.concept_ids.update({t.ent_type for t in doc.tags})
        self.concept2frequency = {}
        for t in doc.tags:
            if t.ent_id not in self.concept2frequency:
                self.concept2frequency[t.ent_id] = 1
            else:
                self.concept2frequency[t.ent_id] += 1
            if t.ent_type not in self.concept2frequency:
                self.concept2frequency[t.ent_type] = 1
            else:
                self.concept2frequency[t.ent_type] += 1

        self.subject_ids = set([s.subject_id for s in doc.extracted_statements])
        self.object_ids = set([s.object_id for s in doc.extracted_statements])
        self.statement_concepts = set([(s.subject_id, s.object_id) for s in doc.extracted_statements])

    def get_text(self):
        return self.document.get_text_content(sections=True)

    def to_dict(self):
        return {"document": self.document.to_dict(),
                "concepts": str(self.concept_ids),
                "concept2frequency": self.concept2frequency}


class DocumentRetriever:

    def __init__(self):
        self.__cache = {}
        self.session = SessionExtended.get()
        self.generesolver = GeneResolver()
        self.generesolver.load_index()

    def retrieve_narrative_documents(self, document_ids: [int], document_collection: str) -> List[
        AnalyzedNarrativeDocument]:
        if len(document_ids) == 0:
            return []

        document_ids = set(document_ids)
        found_ids = set()
        narrative_documents = []

        if document_collection not in self.__cache:
            self.__cache[document_collection] = {}

        # look which documents have been cached
        for did in document_ids:
            if did in self.__cache[document_collection]:
                found_ids.add(did)
                narrative_documents.append(self.__cache[did])

        remaining_document_ids = document_ids - found_ids
        if len(remaining_document_ids) == 0:
            return []
        narrative_documents_queried = retrieve_narrative_documents_from_database(session=self.session,
                                                                                 document_ids=document_ids,
                                                                                 document_collection=document_collection)


        for doc in narrative_documents:
            translated_gene_ids = []
            for tag in doc.document.tags:
                # Gene IDs need a special handling
                if tag.ent_type == GENE:
                    if ';' in tag.ent_id:
                        for g_id in tag.ent_id.split(';'):
                            try:
                                symbol = self.generesolver.gene_id_to_symbol(g_id.strip()).lower()
                                translated_gene_ids.append(TaggedEntity(document=tag.document,
                                                                        start=tag.start,
                                                                        end=tag.end,
                                                                        text=tag.text,
                                                                        ent_id=symbol,
                                                                        ent_type=GENE))
                            except (KeyError, ValueError):
                                continue
                    else:
                        try:
                            symbol = self.generesolver.gene_id_to_symbol(tag.ent_id).lower()
                            translated_gene_ids.append(TaggedEntity(document=tag.document,
                                                                    start=tag.start,
                                                                    end=tag.end,
                                                                    text=tag.text,
                                                                    ent_id=symbol,
                                                                    ent_type=GENE))
                        except (KeyError, ValueError):
                            pass
            doc.document.tags.extend(translated_gene_ids)

        narrative_documents_queried = [AnalyzedNarrativeDocument(d) for d in narrative_documents_queried]

        # add to cache
        for d in narrative_documents_queried:
            self.__cache[document_collection][d.document.id] = d

        # add them to list
        narrative_documents.extend(narrative_documents_queried)
        return narrative_documents

    def retrieve_document_ids_for_query(self, query: AnalyzedQuery, data_graph: DataGraph):
        q = Query()
        for k in query.keywords:
            q.add_term(k)
        return data_graph.compute_query(q)


class AbstractDocumentRanker:

    def __init__(self, name):
        self.name = name

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass


class EqualDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="EqualDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        return list([(d.document.id, 2.0) for d in narrative_documents])


class ConceptDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="ConceptDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            doc_scores.append((d.document.id, len(query.concepts.intersection(d.concept_ids))))

        return sorted(doc_scores, key=lambda x: x[1], reverse=True)


class ConceptFrequencyDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="ConceptFrequencyDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            concept_frequency = sum([d.concept2frequency[c] for c in query.concepts if c in d.concept2frequency])
            doc_scores.append((d.document.id, concept_frequency))

        return sorted(doc_scores, key=lambda x: x[1], reverse=True)


class StatementPartialOverlapDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="StatementPartialOverlapDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            score = len(query.concepts.intersection(d.subject_ids)) + len(query.concepts.intersection(d.object_ids))
            doc_scores.append((d.document.id, score))

        return sorted(doc_scores, key=lambda x: x[1], reverse=True)


class StatementOverlapDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="StatementOverlapDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            score = 0
            for s in query.concepts:
                for o in query.concepts:
                    if (s, o) in d.statement_concepts:
                        score += 1
            doc_scores.append((d.document.id, score))

        return sorted(doc_scores, key=lambda x: x[1], reverse=True)


class GraphConnectivityDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass


class TagFrequencyRanker(AbstractDocumentRanker):
    def __init__(self):
        super().__init__(name="TagFrequencyRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for doc in narrative_documents:
            concepts: set[str] = doc.concept_ids.intersection(query.concepts)
            score: float = sum([doc.concept2frequency[c] for c in concepts if c in doc.concept2frequency])
            doc_scores.append((doc.document.id, score))
        return sorted(doc_scores, key=lambda x: x[1], reverse=True)


class StatementFrequencyRanker(AbstractDocumentRanker):
    def __init__(self, name="StatementFrequencyRanker"):
        super().__init__(name=name)

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for doc in narrative_documents:
            score = len(self._relevant_statements(query, doc))
            doc_scores.append((doc.document.id, score))
        return sorted(doc_scores, key=lambda x: x[1], reverse=True)

    @staticmethod
    def _relevant_statements(query: AnalyzedQuery, narrative_document: AnalyzedNarrativeDocument):
        rev_stmts = set()
        for stmt in narrative_document.document.extracted_statements:
            if all(c in query.concepts for c in {stmt.subject_id, stmt.object_id}) \
                    or all(c in query.concepts for c in {stmt.subject_id, stmt.object_type}) \
                    or all(c in query.concepts for c in {stmt.subject_type, stmt.object_id}) \
                    or all(c in query.concepts for c in {stmt.subject_type, stmt.object_type}):
                rev_stmts.add(stmt)

        return rev_stmts


class ConfidenceStatementFrequencyRanker(StatementFrequencyRanker):
    def __init__(self):
        super().__init__(name="ConfidenceStatementFrequencyRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for doc in narrative_documents:
            score = sum([s.confidence for s in self._relevant_statements(query, doc)])
            doc_scores.append((doc.document.id, score))
        return sorted(doc_scores, key=lambda x: x[1], reverse=True)


class PathFrequencyRanker(AbstractDocumentRanker):
    def __init__(self, name="PathFrequencyRanker"):
        super().__init__(name=name)

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []

        for doc in narrative_documents:
            graph = self._document_graph(doc)
            stmts = list(self._concept_product(query, doc))
            paths = 0
            for subj, obj in stmts:
                # do not search for self combinations
                if subj == obj:
                    continue
                # skip if one of the values does not exist as a node
                if subj not in graph or obj not in graph:
                    continue
                # count existing paths for a statement and remove them lengthwise starting with the shortest possible.
                while networkx.has_path(graph, subj, obj):
                    shortest_path = networkx.shortest_path(graph, subj, obj)
                    for i in range(len(shortest_path) - 1):
                        graph.remove_edge(shortest_path[i], shortest_path[i + 1])
                    paths += self._evaluate_path_score(doc, shortest_path)
            doc_scores.append((doc.document.id, paths))

        return sorted(doc_scores, key=lambda x: x[1], reverse=True)

    @staticmethod
    def _evaluate_path_score(doc: AnalyzedNarrativeDocument, shortest_path: list[str]) -> float:
        return len(shortest_path)

    @staticmethod
    def _document_graph(doc: AnalyzedNarrativeDocument) -> networkx.MultiGraph:
        graph: networkx.MultiGraph = networkx.MultiGraph()
        for stmt in doc.document.extracted_statements:
            graph.add_edge(stmt.subject_id, stmt.object_id)
        return graph

    @staticmethod
    def _concept_product(query: AnalyzedQuery, doc: AnalyzedNarrativeDocument):
        concepts: set[str] = doc.concept_ids.intersection(query.concepts)
        return itertools.product(concepts, concepts)


class ConfidencePathFrequencyRanker(PathFrequencyRanker):
    def __init__(self):
        super().__init__(name="ConfidencePathFrequencyRanker")

    @staticmethod
    def _evaluate_path_score(doc: AnalyzedNarrativeDocument, path: list[str]) -> float:
        score = 0

        for i in range(len(path) - 1):
            subj = path[i]
            obj = path[i + 1]

            for stmt in doc.document.extracted_statements:
                if stmt.subject_type == subj and stmt.object_type == obj \
                        or stmt.subject_type == subj and stmt.object_id == obj \
                        or stmt.subject_id == subj and stmt.object_type == obj \
                        or stmt.subject_id == subj and stmt.object_id == obj:
                    score += stmt.confidence
        return score


class AdjacentEdgesRanker(PathFrequencyRanker):
    def __init__(self, name="AdjacentEdgesRanker"):
        super().__init__(name=name)

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for doc in narrative_documents:
            graph = self._document_graph(doc)
            score = self._evaluate_confidence_score(query, doc, graph)
            doc_scores.append((doc.document.id, score))
        return sorted(doc_scores, key=lambda x: x[1], reverse=True)

    @staticmethod
    def _evaluate_confidence_score(query: AnalyzedQuery, doc: AnalyzedNarrativeDocument,
                                   graph: networkx.MultiGraph) -> float:
        return sum((len(graph.edges(c)) for c in query.concepts))


class ConfidenceAdjacentEdgesRanker(AdjacentEdgesRanker):
    def __init__(self):
        super().__init__(name="ConfidenceAdjacentEdgesRanker")

    @staticmethod
    def _evaluate_confidence_score(query: AnalyzedQuery, doc: AnalyzedNarrativeDocument,
                                   graph: networkx.MultiGraph) -> float:
        score: float = 0
        for concept in query.concepts:
            edges = graph.edges(concept)
            for s, o in edges:
                confidences = (stmt.confidence for stmt in doc.document.extracted_statements
                               if (stmt.subject_type == s or stmt.subject_id == s)
                               and (stmt.object_type == o or stmt.object_id == o))
                score += sum(confidences)
        return score
