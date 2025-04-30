from collections import defaultdict
from typing import List, Set

from sqlalchemy import and_

from kgextractiontoolbox.backend.models import Document, Tag, Predication, BULK_MAX_NO_OF_IN_VALUES
from kgextractiontoolbox.document.document import TaggedEntity
from kgextractiontoolbox.document.narrative_document import NarrativeDocument, StatementExtraction
from kgextractiontoolbox.util.helpers import chunks
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES
from narrant.entity.entity import Entity, get_unique_entity_key
from narrant.entity.entityidtranslator import EntityIDTranslator


def get_unique_document_key(document_id: int, document_collection: str) -> str:
    """
    Generates a unique document key as a string
    :param document_id: the document id
    :param document_collection: the document collection
    :return: unique document key
    """
    return f'{document_collection}___{document_id}'


class ScoredDocumentEntity(Entity):
    """
    Scored document entity contains the entity type and id of some entity within a document
    Scores like tf, tf_normalized and coverage can be stored
    """

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(entity_id=entity_id, entity_type=entity_type)
        self.tf = None
        self.tf_normalized = None
        self.coverage = None
        self.score = None

    def set_score(self, score: float):
        self.score = score

    def set_frequency(self, frequency: int, max_entity_count: int):
        self.tf = frequency
        self.tf_normalized = float(frequency) / float(max_entity_count)

    def set_coverage(self, first_pos: int, last_pos: int, text_len: int):
        diff = last_pos - first_pos
        coverage = float(diff) / float(text_len)
        # some taggers produced strange tag positions that may exceed the text range
        self.coverage = max(0.0, min(1.0, coverage))


class ScoredDocumentStatement(StatementExtraction):
    """
    Class that represents a scored document statement
    """

    def __init__(self, subject: ScoredDocumentEntity, relation: str, object: ScoredDocumentEntity):
        super().__init__(subject_id=subject.entity_id, subject_type=subject.entity_type, subject_str="",
                         predicate="", relation=relation,
                         object_id=object.entity_id, object_type=object.entity_type, object_str="",
                         sentence_id=0, confidence=-1.0)
        self.subject = subject
        self.object = object
        self.score = None
        self.confidence = None
        self.frequency = None

    def set_confidence(self, confidence: float):
        assert 0.0 <= confidence <= 1.0
        self.confidence = confidence

    def set_score(self, score: float):
        self.score = score

    def set_frequency(self, frequency: int):
        self.frequency = frequency

    def has_equal_entities(self, other) -> bool:
        """
        Test whether two scored document statement have equal entities (either s1=s2 && o1=o2) or (s1=o2 && o1=s2)
        :param other:
        :return:
        """
        return (self.subject.get_unique_key() == other.subject.get_unique_key() and
                self.object.get_unique_key() == other.object.get_unique_key()) or \
            (self.object.get_unique_key() == other.subject.get_unique_key() and
             self.subject.get_unique_key() == other.object.get_unique_key())

    def has_overlapping_entities(self, other) -> bool:
        """
        Returns true if both statements have at least a shared entity
        :param other:
        :return:
        """
        return self.subject.get_unique_key() == other.subject.get_unique_key() or \
            self.object.get_unique_key() == other.object.get_unique_key() or \
            self.object.get_unique_key() == other.subject.get_unique_key() or \
            self.subject.get_unique_key() == other.object.get_unique_key()

    def get_unique_key(self):
        return '___'.join([self.subject.get_unique_key(), self.relation, self.object.get_unique_key()])

    def __hash__(self):
        return hash(self.get_unique_key())

    def __eq__(self, other):
        return self.get_unique_key() == other.get_unique_key()


class IndexedDocument(NarrativeDocument):
    """
    Class that represents a narrative document with generated index data,
    """

    def __init__(self, nd: NarrativeDocument, document_collection: str):
        super().__init__(document_id=nd.id, title=nd.title, abstract=nd.abstract,
                         metadata=nd.metadata, tags=nd.tags, sentences=nd.sentences,
                         extracted_statements=nd.extracted_statements)

        self.document_collection = document_collection
        self.first_stage_score = None
        self.extracted_statements = [s for s in self.extracted_statements if s.relation]
        self.classification = nd.classification

        self.scored_entities: [ScoredDocumentEntity] = set()
        self.max_entity_frequency = 0
        self.text_len = len(self.get_text_content(sections=True))
        self.compute_scored_entity_information()
        self.entity_key2scored_entity = {e.get_unique_key(): e for e in self.scored_entities}

        self.scored_statements: [ScoredDocumentStatement] = set()
        self.entity_key2statements = {}
        self.extracted_stmt2scored_statement = {}
        self.compute_scored_statement_information()

    def get_unique_key(self):
        return get_unique_document_key(self.id, self.document_collection)

    def compute_scored_entity_information(self):
        """
        Computes the set of scored entities within this document
        We compute tf, tf_normalized and coverage scores
        :return:
        """
        entity2frequency = {}
        entity2last_position = {}
        entity2first_position = {}
        # singleton implementation
        entityidtranslator = EntityIDTranslator()
        for t in self.tags:
            # translate gene ids to symbols to be compatible to statement gene representation
            try:
                translated_id = entityidtranslator.translate_entity_id(t.ent_id, t.ent_type)
            # some rare genes may not be present in our translation table, just use them as they are
            except KeyError:
                translated_id = t.ent_id
            e = ScoredDocumentEntity(entity_type=t.ent_type, entity_id=translated_id)
            self.scored_entities.add(e)
            entity_key = e.get_unique_key()
            if entity_key not in entity2frequency:
                entity2frequency[entity_key] = 1
                entity2first_position[entity_key] = t.start
                entity2last_position[entity_key] = t.end
            else:
                entity2frequency[entity_key] += 1
                entity2first_position[entity_key] = min(entity2first_position[entity_key], t.start)
                entity2last_position[entity_key] = max(entity2last_position[entity_key], t.end)

        if len(entity2frequency) > 0:
            self.max_entity_frequency = max(v for _, v in entity2frequency.items())

        for e in self.scored_entities:
            e.set_frequency(frequency=entity2frequency[e.get_unique_key()], max_entity_count=self.max_entity_frequency)
            e.set_coverage(first_pos=entity2first_position[e.get_unique_key()],
                           last_pos=entity2last_position[e.get_unique_key()],
                           text_len=self.text_len)

    def compute_scored_statement_information(self):
        """
        Compute information for scored statements, i.e. the set of known statements plus their confidence scores
        :return:
        """

        key2stmts = defaultdict(list)
        if self.extracted_statements:
            for statement in self.extracted_statements:
                key = (statement.subject_type, statement.subject_id, statement.relation,
                       statement.object_type, statement.object_id)
                key2stmts[key].append(statement)

                if statement.relation in SYMMETRIC_PREDICATES:
                    key = (statement.object_type, statement.object_id,
                           statement.relation,
                           statement.subject_type, statement.subject_id)
                    key2stmts[key].append(statement)

        for key, statements in key2stmts.items():
            subject_type, subject_id, relation, object_type, object_id = key
            subject_key = get_unique_entity_key(entity_type=subject_type, entity_id=subject_id)
            object_key = get_unique_entity_key(entity_type=object_type, entity_id=object_id)
            # This situation should not happen often in practice
            # but in some situations we have old statements that do not refer to existing
            # concepts in documents anymore
            # we ignore these statements for ranking purposes
            if subject_key not in self.entity_key2scored_entity:
                continue
            if object_key not in self.entity_key2scored_entity:
                continue

            scored_statement = ScoredDocumentStatement(subject=self.entity_key2scored_entity[subject_key],
                                                       relation=relation,
                                                       object=self.entity_key2scored_entity[object_key])

            scored_statement.set_confidence(max([s.confidence for s in statements]))
            scored_statement.set_frequency(len(statements))
            self.scored_statements.add(scored_statement)
            # all statements are different extractions, but are scored in the same way
            # i.e. the scored statement represents all of them
            for s in statements:
                self.extracted_stmt2scored_statement[s] = scored_statement

            for entity_key in [subject_key, object_key]:
                if entity_key in self.entity_key2statements:
                    self.entity_key2statements[entity_key].append(scored_statement)
                else:
                    self.entity_key2statements[entity_key] = [scored_statement]


def retrieve_indexed_documents_from_database_small(session, document_ids: Set[int], document_collection: str) \
        -> List[IndexedDocument]:
    """
    Retrieves a set of indexed documents from the database
    :param session: the current session
    :param document_ids: a set of document ids
    :param document_collection: the corresponding document collection
    :return: a list of IndexedDocuments
    """
    doc_results = {}

    document_ids_input = sorted(list(document_ids))
    for document_ids_chunk in chunks(document_ids_input, BULK_MAX_NO_OF_IN_VALUES):

        # first query document titles and abstract
        doc_query = session.query(Document).filter(and_(Document.id.in_(document_ids_chunk),
                                                        Document.collection == document_collection))

        for res in doc_query:
            doc_results[res.id] = NarrativeDocument(document_id=res.id, title=res.title, abstract=res.abstract)

        # Next query for all tagged entities in that document
        tag_query = session.query(Tag).filter(and_(Tag.document_id.in_(document_ids_chunk),
                                                   Tag.document_collection == document_collection))
        tag_result = defaultdict(list)
        for res in tag_query:
            tag_result[res.document_id].append(TaggedEntity(document=res.document_id,
                                                            start=res.start,
                                                            end=res.end,
                                                            ent_id=res.ent_id,
                                                            ent_type=res.ent_type,
                                                            text=res.ent_str))
        for doc_id, tags in tag_result.items():
            doc_results[doc_id].tags = tags
            doc_results[doc_id].sort_tags()

        # Next query for extracted statements
        es_query = session.query(Predication)
        es_query = es_query.filter(Predication.document_collection == document_collection)
        es_query = es_query.filter(Predication.document_id.in_(document_ids_chunk))
        es_query = es_query.filter(Predication.relation != None)

        es_for_doc = defaultdict(list)
        for res in es_query:
            es_for_doc[res.document_id].append(StatementExtraction(subject_id=res.subject_id,
                                                                   subject_type=res.subject_type,
                                                                   subject_str=res.subject_str,
                                                                   predicate=res.predicate,
                                                                   relation=res.relation,
                                                                   object_id=res.object_id,
                                                                   object_type=res.object_type,
                                                                   object_str=res.object_str,
                                                                   sentence_id=res.sentence_id,
                                                                   confidence=res.confidence))

        for doc_id, extractions in es_for_doc.items():
            doc_results[doc_id].extracted_statements = extractions

    if len(doc_results) != len(document_ids):
        diff = set(document_ids) - doc_results.keys()
        raise ValueError(f'Did not retrieve all required {document_collection} documents (missed ids: {diff})')

    return [IndexedDocument(d, document_collection) for d in doc_results.values()]
