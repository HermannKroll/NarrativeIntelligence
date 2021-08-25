import logging
from collections import namedtuple
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import Column, String, Float, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, \
    BigInteger, func, insert

import narrant
from narrant.backend.models import Base, DatabaseTable

BULK_QUERY_CURSOR_COUNT_DEFAULT = 10000

Extended = Base

PredicationResult = namedtuple('PredicationResult', ["id", "document_id", "document_collection",
                                                     "subject_id", "subject_str", "subject_type",
                                                     "predicate", "relation",
                                                     "object_id", "object_str", "object_type",
                                                     "confidence", "sentence_id", "extraction_type"])


class Document(narrant.backend.models.Document):
    pass


class Tag(narrant.backend.models.Tag):
    pass


class Tagger(narrant.backend.models.Tagger):
    pass


class DocTaggedBy(narrant.backend.models.DocTaggedBy):
    pass


class DocumentTranslation(narrant.backend.models.DocumentTranslation):
    pass


class DocumentMetadata(Extended, DatabaseTable):
    __tablename__ = 'document_metadata'
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', sqlite_on_conflict='IGNORE')
    )

    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    authors = Column(String, nullable=True)
    journals = Column(String, nullable=True)
    publication_year = Column(String, nullable=True)


class DocumentMetadataService(Extended, DatabaseTable):
    __tablename__ = 'document_metadata_service'
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', sqlite_on_conflict='IGNORE')
    )

    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    title = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    journals = Column(String, nullable=True)
    publication_year = Column(String, nullable=True)


class Predication(Extended, DatabaseTable):
    __tablename__ = "predication"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        ForeignKeyConstraint(('sentence_id',), ('sentence.id',)),
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE'),
        # TODO: This index will consume much disk space around 1.2 times the table size
        #    UniqueConstraint('document_id', 'document_collection', 'subject_id', 'subject_type',
        #                    'predicate', 'object_id', 'object_type', 'extraction_type', 'sentence_id',
        #                   sqlite_on_conflict='IGNORE'),
    )

    id = Column(BigInteger, autoincrement=True)
    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    subject_str = Column(String, nullable=False)
    subject_type = Column(String, nullable=False)
    predicate = Column(String, nullable=False, index=True)
    relation = Column(String, nullable=True)
    object_id = Column(String, nullable=False)
    object_str = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    sentence_id = Column(BigInteger, nullable=False)
    extraction_type = Column(String, nullable=False)

    def __str__(self):
        return "<{} ({})>\t<{}>\t<{} ({})>".format(self.subject_id, self.subject_type,
                                                   self.relation,
                                                   self.object_id, self.object_type)

    def __repr__(self):
        return "<Predication {}>".format(self.id)

    @staticmethod
    def iterate_predications(session, document_collection=None,
                             bulk_query_cursor_count=BULK_QUERY_CURSOR_COUNT_DEFAULT):
        pred_query = session.query(Predication).filter(Predication.relation != None)
        if document_collection:
            pred_query = pred_query.filter(Predication.document_collection == document_collection)
        pred_query = pred_query.yield_per(bulk_query_cursor_count)
        for res in pred_query:
            yield res

    @staticmethod
    def iterate_predications_joined_sentences(session, document_collection=None,
                                              bulk_query_cursor_count=BULK_QUERY_CURSOR_COUNT_DEFAULT):
        pred_query = session.query(Predication, Sentence).join(Sentence, Predication.sentence_id == Sentence.id) \
            .filter(Predication.relation != None)
        if document_collection:
            pred_query = pred_query.filter(Predication.document_collection == document_collection)
        pred_query = pred_query.yield_per(bulk_query_cursor_count)
        for res in pred_query:
            yield res

    @staticmethod
    def query_predication_count(session, document_collection=None, relation=None):
        """
        Counts the number of rows in Predicate
        :param session: session handle
        :param document_collection: count only in document collection
        :param relation: if given the predication is filtered by this relation
        :return: the number of rows
        """
        query = session.query(Predication)
        if document_collection:
            query = query.filter(Predication.document_collection == document_collection)
        if relation:
            query = query.filter(Predication.relation == relation)
        return query.count()

    @staticmethod
    def query_predicates_with_count(session, document_collection=None) -> List[Tuple[str, int]]:
        """
        Queries predicates with the corresponding count of tuples
        :param session: session handle
        :param document_collection: document collection
        :return: a list of tuples (predicate, count of entries)
        """
        if not document_collection:
            query = session.query(Predication.predicate, func.count(Predication.predicate)) \
                .group_by(Predication.predicate)
        else:
            query = session.query(Predication.predicate, func.count(Predication.predicate)) \
                .filter(Predication.document_collection == document_collection) \
                .group_by(Predication.predicate)

        predicates_with_count = []
        start_time = datetime.now()
        for r in session.execute(query):
            predicates_with_count.append((r[0], int(r[1])))
        logging.info('{} predicates queried in {}s'.format(len(predicates_with_count), datetime.now() - start_time))
        return sorted(predicates_with_count, key=lambda x: x[1], reverse=True)

    @staticmethod
    def query_predicates_with_mapping_and_count(session, document_collection=None) -> List[Tuple[str, str, int]]:
        """
        Queries predicates with the corresponding relation mapping and count of tuples
        :param session: session handle
        :param document_collection: document collection
        :return: a list of tuples (predicate, relation, count of entries)
        """
        if not document_collection:
            query = session.query(Predication.predicate, Predication.relation,
                                  func.count(Predication.predicate)) \
                .group_by(Predication.predicate, Predication.relation)
        else:
            query = session.query(Predication.predicate, Predication.relation,
                                  func.count(Predication.predicate)) \
                .filter(Predication.document_collection == document_collection) \
                .group_by(Predication.predicate, Predication.relation)

        predicates_with_count = []
        start_time = datetime.now()
        for r in session.execute(query):
            predicates_with_count.append((r[0], r[1], int(r[2])))
        logging.info('{} predicates queried in {}s'.format(len(predicates_with_count), datetime.now() - start_time))
        return sorted(predicates_with_count, key=lambda x: x[2], reverse=True)


class PredicationDenorm(Extended, DatabaseTable):
    __tablename__ = "predication_denorm"
    __table_args__ = (
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE'),
    )
    id = Column(BigInteger, nullable=False, autoincrement=True)
    subject_id = Column(String, nullable=False, index=True)
    subject_type = Column(String, nullable=False, index=True)
    relation = Column(String, nullable=False, index=True)
    object_id = Column(String, nullable=False, index=True)
    object_type = Column(String, nullable=False, index=True)
    provenance_mapping = Column(String, nullable=False)


class PredicationRating(Extended, DatabaseTable):
    __tablename__ = "predication_rating"
    __table_args__ = (
        ForeignKeyConstraint(('predication_id',), ('predication.id',)),
        PrimaryKeyConstraint('user_id', 'query', 'predication_id', sqlite_on_conflict='IGNORE')
    )
    user_id = Column(String)
    query = Column(String)
    predication_id = Column(BigInteger)
    rating = Column(String)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)

    @staticmethod
    def insert_user_rating(session, user_id: str, query: str, predication_id: int, rating: str):
        insert_stmt = insert(PredicationRating).values(user_id=user_id, query=query, predication_id=predication_id,
                                                       rating=rating)
        session.execute(insert_stmt)
        session.commit()


class PredicationToDelete(Extended, DatabaseTable):
    __tablename__ = "predication_to_delete"
    __table_args__ = (
        PrimaryKeyConstraint('predication_id', sqlite_on_conflict='IGNORE'),
    )
    predication_id = Column(BigInteger)


class Sentence(Extended, DatabaseTable):
    __tablename__ = "sentence"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE')
    )

    id = Column(BigInteger)
    document_id = Column(BigInteger, nullable=False, index=True)
    document_collection = Column(String, nullable=False, index=True)
    text = Column(String, nullable=False)
    md5hash = Column(String, nullable=False)

    @staticmethod
    def iterate_sentences(session, document_collection=None, bulk_query_cursor_count=BULK_QUERY_CURSOR_COUNT_DEFAULT):
        sent_query = session.query(Sentence)
        if document_collection:
            sent_query = sent_query.filter(Sentence.document_collection == document_collection)
        sent_query = sent_query.yield_per(bulk_query_cursor_count)
        for res in sent_query:
            yield res


class DocProcessedByIE(Extended, DatabaseTable):
    __tablename__ = "doc_processed_by_ie"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', 'extraction_type', sqlite_on_conflict='IGNORE')
    )
    document_id = Column(BigInteger)
    document_collection = Column(String)
    extraction_type = Column(String)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)
