import logging
from typing import List

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.entity.entitytagger import EntityTagger
from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import ScoredDocumentEntity, retrieve_indexed_documents_from_database_small, \
    IndexedDocument
from narraint.ranking.scoring import score_edge_by_tfidf_coverage_confidence
from narrant.entity.entityresolver import EntityResolver


def pairwise(iterable):
    """
    Function taken from package itertools since it is added in Python 3.10.
    See https://docs.python.org/3/library/itertools.html#itertools.pairwise.

    pairwise('ABCDEFG') → AB BC CD DE EF FG

    :param iterable: iterable object
    :return: tuple pairs
    """

    iterator = iter(iterable)
    a = next(iterator, None)

    for b in iterator:
        yield a, b
        a = b


class PatternDiscovery:
    TOP_NEWEST_DOCUMENTS = 1000
    TOP_ENTITIES = 1

    def __init__(self):
        self.tagger = EntityTagger()
        self.resolver = EntityResolver()
        self.corpus = DocumentCorpus()

    def concept_to_document_ids(self, concept: str, document_collections: List[str], session):
        """
        Translate a concept string to its most important document ids. Therefore, the
        concepts are translated first into known entities and sorted by their support score.
        The documents for the remaining top scored entities are fetched and returned.
        Note, that the retrieved documents are unified into one list.
        :param concept: concept string
        :param document_collections: list of document collection the documents are retrieved from
        :param session: SQL database session
        :return: list of relevant document ids for the concept
        """
        # find matching entities
        entities = self.tagger.tag_entity(concept)
        entities = list(ScoredDocumentEntity(e.entity_type, e.entity_id) for e in set(entities))

        # calculate entity scores
        entity_support = [self.corpus.get_entity_support(e) for e in entities]
        # score entities by support (occurrence) and select the top k
        entity_support = sorted(zip(entities, entity_support), key=lambda x: x[1], reverse=True)

        entities = list()
        entity_ids = list()
        entity_types = list()
        for entity, _ in entity_support[:self.TOP_ENTITIES]:
            entity_ids.append(entity.entity_id)
            entity_types.append(entity.entity_type)
            entities.append(entity.get_unique_key())
        entity_types = list(set(entity_types))

        # retrieve relevant documents
        collection2ids = TagInvertedIndex.retrieve_document_ids_for_entities(session, entity_ids, entity_types,
                                                                             document_collections)
        return collection2ids, entities

    def score_document_statements(self, scored_documents: List[IndexedDocument]):
        """
        Compute a list of statements from a list of documents. The list contains
        unique statements ordered by their support score (descending).
        If a statement occurs multiple times (in different documents), the score
        is summed up. If the corresponding parameter IGNORE_ASSOCIATED_RELATION
        is set, ASSOCIATED relations are ignored.
        :param scored_documents: list of scored documents
        :return: list of ordered statements
        """
        statement2score = dict()
        key2statement = dict()
        for indexed_document in scored_documents:
            for scored_statement in indexed_document.scored_statements:
                score = score_edge_by_tfidf_coverage_confidence(statement=scored_statement, corpus=self.corpus)
                statement_key = scored_statement.get_unique_key()

                if statement_key not in statement2score:
                    statement2score[statement_key] = score
                    key2statement[statement_key] = scored_statement
                else:
                    statement2score[statement_key] += score

        # sort by highest score
        statements = sorted(statement2score.items(), key=lambda x: x[1], reverse=True)
        statements = list(statement for statement, _ in statements)
        return statements, key2statement

    @staticmethod
    def relevant_statements_for_concepts(statements: list, concept2entity: dict, key2statement: dict,
                                         num_edges: int) -> set:
        """
        Get the first TOP_STATEMENTS relevant to a concept. It is checked
        whether an identical statement is present in the list of selected
        statements, e.g., by flipping subject and object. Statements are
        only considered, if they contain one of the concepts entities to
        omit paths that are not interesting for the target pattern.
        :param key2statement: dict with statement-key to statement translations
        :param concept2entity: dict with concepts to entity translations
        :param statements: list of statements relevant to the concept
        :param num_edges: number of relevant edges for one concept
        :return: list of statements relevant to the concept's entities
        """
        relevant_statements = set()
        known_statements = set()
        for _, concept_entities in concept2entity.items():
            concept_relevant_statements = set()
            for statement in statements:
                subject_key = key2statement[statement].subject.get_unique_key()
                object_key = key2statement[statement].object.get_unique_key()

                # components do not contain a concepts entity
                if (subject_key not in concept_entities
                        and object_key not in concept_entities):
                    continue

                # statement already known
                if ((subject_key, object_key) in known_statements
                        or (object_key, subject_key) in known_statements):
                    continue

                concept_relevant_statements.add(statement)
                known_statements.add((subject_key, object_key))
                if len(concept_relevant_statements) >= num_edges:
                    break

                relevant_statements |= concept_relevant_statements
        return relevant_statements

    def discover_pattern_for_documents(self, documents: List[QueryDocumentResult], concept2entity: dict,
                                       num_edges: int):
        """
        Create a graph of patterns that occur frequently in the document collection.
        The algorithm selects the newest 1k documents and retrieves the top scored
        statements for each statement.
        :param documents: list of QueryResultDocuments
        :param concept2entity: dictionary mapping concept strings to entities
        :param num_edges: number of edges for each concept
        :return: pattern-graph, list of entities to highlight, and the documents.
        """

        session = SessionExtended.get()

        # 1. take the newest TOP_NEWEST_DOCUMENTS documents
        documents = documents[:self.TOP_NEWEST_DOCUMENTS]

        # collect documents with same collections
        collection2ids = dict()
        for document in documents:
            if document.document_collection not in collection2ids:
                collection2ids[document.document_collection] = {document.document_id}
            else:
                collection2ids[document.document_collection].add(document.document_id)

        # 2. retrieve indexed documents
        indexed_documents = list()
        for collection, ids in collection2ids.items():
            indexed_documents.extend(retrieve_indexed_documents_from_database_small(session=session,
                                                                                    document_ids=ids,
                                                                                    document_collection=collection))

        # 3. score all statements (sum up scores of duplicated statements)
        statements, key2statement = self.score_document_statements(scored_documents=indexed_documents)

        # 4. find top k statements for each concept
        relevant_statements = self.relevant_statements_for_concepts(statements=statements,
                                                                    concept2entity=concept2entity,
                                                                    key2statement=key2statement,
                                                                    num_edges=num_edges)
        # 5. build pattern graph
        graph = set()
        concept_nodes = set()
        known_statement_pairs = set()
        relevant_entities = set.union(*concept2entity.values())
        for statement_key in relevant_statements:
            subject_id = key2statement[statement_key].subject.entity_id
            subject_type = key2statement[statement_key].subject.entity_type
            subject_key = key2statement[statement_key].subject.get_unique_key()
            object_id = key2statement[statement_key].object.entity_id
            object_type = key2statement[statement_key].object.entity_type
            object_key = key2statement[statement_key].object.get_unique_key()

            try:
                subject_name = self.resolver.get_name_for_var_ent_id(subject_id, subject_type)
            except KeyError:
                subject_name = subject_id
            try:
                object_name = self.resolver.get_name_for_var_ent_id(object_id, object_type)
            except KeyError:
                object_name = object_id

            if ((subject_name, object_name) in known_statement_pairs
                    or (object_name, subject_name) in known_statement_pairs):
                # Duplicates occur during the following issue:
                # il6, antibody, rheumatism
                # -> rheumatism - the following statements occur:
                #   - (('MESH:D001169', 'Disease'), ('MESH:D001172', 'Disease'))
                #   - (('MESH:D001169', 'Method'), ('MESH:D001172', 'Disease'))
                # The resolver resolves both subjects to the same string: 'Arthritis, Experimental'.
                # Since the frontend ignores the relation, we need to filter for duplicate statements.
                continue

            relation = key2statement[statement_key].relation
            graph.add((subject_name, subject_type, relation, object_name, object_type))

            # find relevant components and store their translations separately
            if subject_key in relevant_entities:
                concept_nodes.add((subject_name, subject_type))
            if object_key in relevant_entities:
                concept_nodes.add((object_name, object_type))

        # map them as a dict to be json-compatible
        concept_nodes = {entity_name: entity_type for entity_name, entity_type in concept_nodes}
        return documents, list(graph), concept_nodes

    def retrieve_relevant_documents_for_concepts(self, concepts: List[str], document_collections: List[str]):
        logging.info(f"Compute pattern for concepts: {concepts}")
        session = SessionExtended.get()

        collection2ids = dict()
        concept2entities = dict()
        for concept in concepts:
            concept_collection2ids, entities = self.concept_to_document_ids(concept=concept, session=session,
                                                                            document_collections=document_collections)

            for collection, ids in concept_collection2ids.items():
                if collection not in collection2ids:
                    collection2ids[collection] = ids
                else:
                    collection2ids[collection].intersection_update(ids)
            concept2entities[concept] = set(entities)
        return collection2ids, concept2entities
