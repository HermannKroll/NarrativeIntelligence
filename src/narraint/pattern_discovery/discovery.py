import logging
from typing import List, Dict, Tuple, Set

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.entity.entity import TranslatedEntity
from narraint.entity.entitytagger import EntityTagger
from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import ScoredDocumentEntity, retrieve_indexed_documents_from_database_small, \
    IndexedDocument, ScoredDocumentStatement
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
    MAX_EDGES_PER_CONCEPT = 50

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

    def score_document_statements(self, scored_documents: List[IndexedDocument]) \
            -> Tuple[List[str], Dict[str, ScoredDocumentStatement]]:
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

    def relevant_statements_for_concepts(self, statements: List[str], concept2entity: Dict[str, TranslatedEntity],
                                         key2statement: Dict[str, ScoredDocumentStatement]) -> Dict[Tuple, List[str]]:
        """
        For each concept, get MAX_EDGES_PER_CONCEPT edges. It is checked
        whether an identical statement is present in the list of selected
        statements, e.g., by flipping subject and object. Statements are
        only considered, if they contain one of the concepts entities to
        omit paths that are not interesting for the target pattern.
        :param key2statement: dict with statement-key to statement translations
        :param concept2entity: dict with concepts to entity translations
        :param statements: list of statements relevant to the concept
        :return: list of statements relevant to the concept's entities
        """
        known_statements = set()
        concept2relevant_statements = dict()
        for concept, concept_entities in concept2entity.items():
            concept_relevant_statements = list()
            concept_entity = None
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

                concept_relevant_statements.append(statement)
                known_statements.add((subject_key, object_key))

                # get concept entity information if possible
                if not concept_entity and subject_key in concept_entities:
                    concept_entity = key2statement[statement].subject
                elif not concept_entity and object_key in concept_entities:
                    concept_entity = key2statement[statement].object

                if len(concept_relevant_statements) >= self.MAX_EDGES_PER_CONCEPT:
                    break

            if not concept_entity:
                raise KeyError("Could not find entity information for: {}".format(concept))
            concept2relevant_statements[concept_entity] = concept_relevant_statements
        return concept2relevant_statements

    def entity_to_name(self, entity) -> Tuple[str, str]:
        try:
            entity_name = self.resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type)
        except KeyError:
            entity_name = entity.entity_id
        return entity_name, entity.entity_type

    def discover_pattern_for_documents(self, documents: List[QueryDocumentResult],
                                       concept2entity: Dict[str, Set[TranslatedEntity]]) \
            -> Tuple[List[QueryDocumentResult], Dict]:
        """
        Create a graph of patterns that occur frequently in the document collection.
        The algorithm selects the newest 1k documents and retrieves the top scored
        statements for each statement.
        :param documents: list of QueryResultDocuments
        :param concept2entity: dictionary mapping concept strings to entities
        :return: documents, concept2statements.
        """

        session = SessionExtended.get()

        # 1. take the newest TOP_NEWEST_DOCUMENTS documents
        if len(documents) > self.TOP_NEWEST_DOCUMENTS:
            logging.info(f"Got {len(documents)} documents. Cut after {self.TOP_NEWEST_DOCUMENTS} documents.")
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
        concept2relevant_statements = self.relevant_statements_for_concepts(statements=statements,
                                                                            concept2entity=concept2entity,
                                                                            key2statement=key2statement)
        # 5. build pattern graph and translate the entities
        concept2graph = dict()
        known_statement_pairs = set()
        for concept, statement_keys in concept2relevant_statements.items():
            concept_statements = list()
            for statement_key in statement_keys:
                subject = key2statement[statement_key].subject
                object_ = key2statement[statement_key].object

                subject_name, subject_type = self.entity_to_name(subject)
                object_name, object_type = self.entity_to_name(object_)

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
                concept_statements.append((subject_name, subject.entity_type, object_name, object_.entity_type))
                known_statement_pairs.add((subject_name, object_name))

            concept_name, _ = self.entity_to_name(concept)
            concept2graph[concept_name] = concept_statements
        return documents, concept2graph

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
