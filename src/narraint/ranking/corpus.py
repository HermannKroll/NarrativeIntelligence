import logging
import math

from tqdm import tqdm

from kgextractiontoolbox.backend.models import Document
from kgextractiontoolbox.document.narrative_document import StatementExtraction
from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.ranking.indexed_document import IndexedDocument

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


class DocumentCorpus:
    """
    Singleton class that can compute tf-idf scores for statements and entities
    """
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self):
        logging.info('Querying available document collections...')
        session = SessionExtended.get()
        self.collections = set()
        self.all_idf_data_cached = False
        for row in session.query(Document.collection).distinct():
            self.collections.add(row.collection)

        logging.info(f'Retrieving size of document corpus (collections = {self.collections})')
        self.document_count = 0
        for collection in self.collections:
            logging.info(f'Counting documents in collection: {collection}')
            col_count = session.query(Document.id).filter(Document.collection == collection).count()
            self.document_count += col_count
            logging.info(f'{col_count} documents found')

        logging.info(f'{self.document_count} documents in corpus')
        self.cache_concept2support = dict()
        self.__load_all_support_into_memory()

    def __load_all_support_into_memory(self):
        """
        Transfers all tag inverted index information into main memory
        :return:
        """
        session = SessionExtended.get()

        logging.info('Caching all concept inverted index support entries...')
        total = session.query(TagInvertedIndex).count()
        q = session.query(TagInvertedIndex.entity_type,
                          TagInvertedIndex.entity_id,
                          TagInvertedIndex.document_collection,
                          TagInvertedIndex.support)
        for row in tqdm(q, desc="Loading db data...", total=total):
            key = (row.entity_type, row.entity_id)
            if key in self.cache_concept2support:
                self.cache_concept2support[key] += row.support
            else:
                self.cache_concept2support[key] = row.support
        self.all_idf_data_cached = True
        logging.info('Finished')

    def get_entity_ifd_score(self, entity_type: str, entity_id: str) -> float:
        """
        Computes the tf-idf score for an entity (normalized)
        :param entity_type: the entity type
        :param entity_id: the entity id
        :return: a score between 0 and 1
        """
        return math.log(self.get_document_count() / self.get_entity_support(entity_type, entity_id)) / math.log(
            self.document_count)

    def get_document_count(self) -> int:
        """
        Gets the number of all documents
        :return: the number of all documents
        """
        return self.document_count

    def get_entity_support(self, entity_type: str, entity_id: str) -> int:
        """
        Gets the number of documents that include a specific entity
        :param entity_type: the entity type
        :param entity_id: the entity id
        :return: the number of documents containing that entity
        """
        key = (entity_type, entity_id)
        if key in self.cache_concept2support:
            return self.cache_concept2support[key]
        # not in index, but all data should be loaded. so no retrieval is needed any more
        # however, some strange statement concept might not appear in the concept index
        else:
            return 1

    def score_edge_by_tf_and_concept_idf(self, statement: StatementExtraction, document: IndexedDocument) -> float:
        """
        Computes a statement's score defined as follows:
        score = confidence * coverage * 1/2 * (tfidf (subject) + tfidf(object)
        :param statement: a statement
        :param document: an indexed document
        :return: a score between 0 and 1
        """
        confidence = document.get_statement_confidence(statement)

        if document.concept_count > 0:
            tf_s = document.get_entity_tf(statement.subject_type, statement.subject_id) / document.concept_count
            tf_o = document.get_entity_tf(statement.object_type, statement.object_id) / document.concept_count
        else:
            tf_s = 0.0
            tf_o = 0.0
        idf_s = self.get_entity_ifd_score(statement.subject_type, statement.subject_id)
        idf_o = self.get_entity_ifd_score(statement.object_type, statement.object_id)

        tfidf = PREDICATE_TO_SCORE[statement.relation] * (0.5 * ((tf_s * idf_s) + (tf_o * idf_o)))

        coverage = min(document.get_entity_coverage(statement.subject_type, statement.subject_id),
                       document.get_entity_coverage(statement.object_type, statement.object_id))

        return coverage * confidence * tfidf

    def get_concept_support(self, entity_id):
        if entity_id in self.cache_concept2support:
            return self.cache_concept2support[entity_id]
        # not in index, but all data should be loaded. so no retrieval is needed any more
        # however, some strange statement concept might not appear in the concept index
        if self.all_idf_data_cached:
            return 1

        session = SessionExtended.get()
        q = session.query(TagInvertedIndex.support)
        q = q.filter(TagInvertedIndex.entity_id == entity_id)
        support = 0
        for row in q:
            support += row.support

        if support == 0:
            support = 1

        self.cache_concept2support[entity_id] = support
        return support

    def get_concept_ifd_score(self, entity_id: str):
        return math.log(self.get_document_count() / self.get_concept_support(entity_id)) / math.log(
            self.document_count)
