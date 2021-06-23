from collections import namedtuple
from datetime import datetime

import logging
from typing import List, Tuple

from sqlalchemy import Column, String, Float, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, \
    BigInteger, func, insert

import narrant
from narrant.backend.models import Base

Extended = Base

PredicationResult = namedtuple('PredicationResult', ["id", "document_id", "document_collection",
                                                     "subject_id", "subject_str", "subject_type",
                                                     "predicate", "predicate_canonicalized",
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


class DocumentMetadata(Extended):
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


class Predication(Extended):
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
    predicate_canonicalized = Column(String, nullable=True)
    object_id = Column(String, nullable=False)
    object_str = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    sentence_id = Column(BigInteger, nullable=False)
    extraction_type = Column(String, nullable=False)

    def __str__(self):
        return "<{} ({})>\t<{}>\t<{} ({})>".format(self.subject_id, self.subject_type,
                                              self.predicate_canonicalized,
                                              self.object_id, self.object_type)

    def __repr__(self):
        return "<Predication {}>".format(self.id)

    @staticmethod
    def query_predication_count(session, predicate_canonicalized=None):
        """
        Counts the number of rows in Predicate
        :param session: session handle
        :param predicate_canonicalized: if given the predication is filtered by this predicate_canonicalized
        :return: the number of rows
        """
        if predicate_canonicalized:
            return session.query(Predication).filter(Predication.predicate_canonicalized == predicate_canonicalized) \
                .count()
        else:
            return session.query(Predication).count()

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


class PredicationRating(Extended):
    __tablename__ = "predication_rating"
    __table_args__ = (
        ForeignKeyConstraint(('predication_id',), ('predication.id',)),
        PrimaryKeyConstraint('user_id', 'predication_id', sqlite_on_conflict='IGNORE')
    )
    user_id = Column(String)
    predication_id = Column(BigInteger)
    rating = Column(String)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)

    @staticmethod
    def insert_user_rating(session, user_id: str, predication_id: int, rating: str):
        insert_stmt = insert(PredicationRating).values(user_id=user_id, predication_id=predication_id, rating=rating)
        session.execute(insert_stmt)
        session.commit()


class PredicationToDelete(Extended):
    __tablename__ = "predication_to_delete"
    __table_args__ = (
        PrimaryKeyConstraint('predication_id', sqlite_on_conflict='IGNORE'),
    )
    predication_id = Column(BigInteger)


class Sentence(Extended):
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


class DocProcessedByIE(Extended):
    __tablename__ = "doc_processed_by_ie"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', 'extraction_type', sqlite_on_conflict='IGNORE')
    )
    document_id = Column(BigInteger)
    document_collection = Column(String)
    extraction_type = Column(String)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)


class PredicationDenorm(Extended):
    __tablename__ = "predication_denorm"
    __table_args__ = (
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE'),
    )
    id = Column(BigInteger, nullable=False, autoincrement=True)
    subject_id = Column(String, nullable=False, index=True)
    subject_type = Column(String, nullable=False)
    predicate_canonicalized = Column(String, nullable=False, index=True)
    object_id = Column(String, nullable=False, index=True)
    object_type = Column(String, nullable=False)
    document_ids = Column(String, nullable=False)
    provenance_mapping = Column(String, nullable=False)
