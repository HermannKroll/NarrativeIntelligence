import logging
from typing import List

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.entity.entitytagger import EntityTagger
from narraint.keywords2graph.translation import ASSOCIATED
from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import ScoredDocumentEntity, retrieve_indexed_documents_from_database_small, \
    IndexedDocument
from narraint.ranking.scoring import score_edge_by_tfidf_coverage_confidence
from narrant.entity.entityresolver import EntityResolver

DOCUMENT_COLLECTION = "PubMed"
TOP_STATEMENTS = 10
TOP_ENTITIES = 1
TOP_SHORTEST_PATHS = 5


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
    def __init__(self):
        self.tagger = EntityTagger()
        self.resolver = EntityResolver()
        self.corpus = DocumentCorpus()

        self.concept_to_entities = dict()
        self.relevant_doc_ids = set()
        self.relevant_statements = ()
        self.key_to_statement = dict()

    def concept_to_document_ids(self, concept: str, session):
        # find matching entities
        entities = self.tagger.tag_entity(concept)
        entities = list(ScoredDocumentEntity(e.entity_type, e.entity_id) for e in set(entities))
        logging.info(f"Found translations: {entities}")

        # calculate entity scores
        entity_support = [self.corpus.get_entity_support(e) for e in entities]
        # score entities by support (occurrence) and select the top k
        entity_support = sorted(zip(entities, entity_support), key=lambda x: x[1], reverse=True)
        top_entities = [(e.entity_id, e.entity_type) for e, _ in entity_support][:TOP_ENTITIES]
        logging.info(f"Top {TOP_ENTITIES} entities for {concept}: {top_entities}")

        # retrieve relevant documents
        document_ids = set()
        for entity_id, entity_type in top_entities:
            query = session.query(TagInvertedIndex.document_ids)
            query = query.filter(TagInvertedIndex.entity_type == entity_type,
                                 TagInvertedIndex.entity_id == entity_id,
                                 TagInvertedIndex.document_collection == DOCUMENT_COLLECTION)
            entity_document_ids = TagInvertedIndex.prepare_document_ids(query.first()[0])
            document_ids |= set(entity_document_ids)
        self.concept_to_entities[concept] = set(top_entities)
        return document_ids

    def score_document_statements(self, scored_documents: List[IndexedDocument]):
        statement_to_score = dict()

        for indexed_document in scored_documents:
            for scored_statement in indexed_document.scored_statements:
                if scored_statement.relation == ASSOCIATED:
                    continue

                score = score_edge_by_tfidf_coverage_confidence(statement=scored_statement, corpus=self.corpus)
                statement_key = scored_statement.get_unique_key()

                if statement_key not in statement_to_score:
                    statement_to_score[statement_key] = score
                    self.key_to_statement[statement_key] = scored_statement
                else:
                    statement_to_score[statement_key] += score

        # sort by highest score
        statements = sorted(statement_to_score.items(), key=lambda x: x[1], reverse=True)
        statements = list(statement for statement, _ in statements)
        return statements

    def relevant_statements_for_concept(self, concept: str, statements: list,
                                        threshold: int = TOP_STATEMENTS) -> set:
        relevant_statements = set()
        known_statements = set()
        for statement in statements:
            subject_key = self.key_to_statement[statement].subject.get_unique_key()
            object_key = self.key_to_statement[statement].object.get_unique_key()

            # components do not contain a concepts entity
            if (subject_key not in self.concept_to_entities[concept]
                    and object_key not in self.concept_to_entities[concept]):
                continue

            # statement already known
            if ((subject_key, object_key) in known_statements
                    or (object_key, subject_key) in known_statements):
                continue

            relevant_statements.add(statement)
            known_statements.add((subject_key, object_key))
            if len(relevant_statements) >= threshold:
                break
        return relevant_statements

    def discover_pattern_for_concepts(self, concepts: List[str]):
        logging.info(f"Concept: {concepts}")
        session = SessionExtended.get()

        self.concept_to_entities = dict()
        self.relevant_doc_ids = set()
        self.relevant_statements = ()
        self.key_to_statement = dict()

        # 1. retrieve document ids for concept
        document_ids = set()
        for concept in concepts:
            concept_documents = self.concept_to_document_ids(concept=concept, session=session)
            if len(document_ids) == 0:
                document_ids = concept_documents
            else:
                document_ids.intersection_update(concept_documents)
        logging.info(f"Found {len(document_ids)} documents")

        if len(document_ids) == 0:
            raise Exception("No intersecting documents found")

        # 2. retrieve indexed documents
        logging.info("Retrieve document predications...")
        indexed_documents = retrieve_indexed_documents_from_database_small(session=session,
                                                                           document_ids=document_ids,
                                                                           document_collection=DOCUMENT_COLLECTION)

        # 3. score all statements (sum up scores of duplicated statements)
        logging.info("Calculating statement scores...")
        statements = self.score_document_statements(scored_documents=indexed_documents)

        # 4. find top k statements for each concept
        logging.info("Find relevant statements for each concept...")
        relevant_statements = set()
        for concept in concepts:
            relevant_statements |= self.relevant_statements_for_concept(concept=concept, statements=statements)

        # Duplicates occur during the following issue:
        # il6, antibody, rheumatism
        # -> 4. rheumatism:
        #   the following statements occur:
        #   - (('MESH:D001169', 'Disease'), ('MESH:D001172', 'Disease'))
        #   - (('MESH:D001169', 'Method'), ('MESH:D001172', 'Disease'))
        #   -> two distinct statements
        #   -> the resolver resolves both subjects to the same string 'Arthritis, Experimental'
        #   -> Solution: filter for duplicate statement strings in frontend
        #   -> Question: Should not exist two different nodes with the same name (but different colors due to types)?

        graph_statements = set()
        concept_nodes = set()
        relevant_entities = set.union(*self.concept_to_entities.values())
        print(relevant_entities)
        for statement_key in relevant_statements:
            subject = (self.key_to_statement[statement_key].subject.entity_id,
                       self.key_to_statement[statement_key].subject.entity_type)
            object = (self.key_to_statement[statement_key].object.entity_id,
                      self.key_to_statement[statement_key].object.entity_type)

            try:
                subject_name = self.resolver.get_name_for_var_ent_id(*subject)
            except KeyError:
                subject_name = subject[0]
            try:
                object_name = self.resolver.get_name_for_var_ent_id(*object)
            except KeyError:
                object_name = object[0]
            relation = self.key_to_statement[statement_key].relation
            graph_statements.add((subject_name, subject[1], relation, object_name, object[1]))

            # find relevant components and store their translations separately
            if subject in relevant_entities:
                concept_nodes.add((subject_name, subject[1]))
            if object in relevant_entities:
                concept_nodes.add((object_name, object[1]))
        concept_nodes = {entity_id: entity_type for entity_id, entity_type in concept_nodes}
        return list(graph_statements), concept_nodes, indexed_documents


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    st, cn, docs = PatternDiscovery().discover_pattern_for_concepts(["il6", "antibody", "rheumatism"])
    # s = get_knowledge_path(["aspirin", "headache"])
    print(st)
