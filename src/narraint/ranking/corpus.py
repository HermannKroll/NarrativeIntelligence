import json
import logging
import math

from tqdm import tqdm

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex, ContentData
from narraint.ranking.indexed_document import ScoredDocumentEntity


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

        query = session.query(ContentData).filter(ContentData.name == ContentData.CONTENT_DATA_COLLECTIONS)
        collection2count = {}
        for row in query:
            collection2count = json.loads(row.data)

        self.collections = set(collection2count.keys())

        logging.info(f'Retrieving size of document corpus (collections = {self.collections})')
        self.document_count = 0
        for collection in self.collections:
            logging.info(f'Counting documents in collection: {collection}')
            col_count = int(collection2count[collection])
            self.document_count += col_count
            logging.info(f'{col_count} documents found')

        logging.info(f'{self.document_count} documents in corpus')
        self.cache_entity2support = dict()
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
            key = ScoredDocumentEntity(entity_type=row.entity_type, entity_id=row.entity_id).get_unique_key()
            if key in self.cache_entity2support:
                self.cache_entity2support[key] += row.support
            else:
                self.cache_entity2support[key] = row.support
        self.all_idf_data_cached = True
        logging.info('Finished')

    def get_entity_ifd_score(self, entity: ScoredDocumentEntity) -> float:
        """
        Computes the tf-idf score for an entity (normalized)
        :param entity: the entity
        :return: a score between 0 and 1
        """
        return math.log(self.get_document_count() / self.get_entity_support(entity)) / math.log(self.document_count)

    def get_document_count(self) -> int:
        """
        Gets the number of all documents
        :return: the number of all documents
        """
        return self.document_count

    def get_entity_support(self, entity: ScoredDocumentEntity) -> int:
        """
        Gets the number of documents that include a specific entity
        :param entity: the entity
        :return: the number of documents containing that entity
        """
        key = entity.get_unique_key()
        if key in self.cache_entity2support:
            return self.cache_entity2support[key]
        # not in index, but all data should be loaded. so no retrieval is needed any more
        # however, some strange statement concept might not appear in the concept index
        else:
            return 1

    def get_concept_ifd_score(self, entity: ScoredDocumentEntity) -> float:
        return math.log(self.get_document_count() / self.get_entity_support(entity)) / math.log(
            self.document_count)
