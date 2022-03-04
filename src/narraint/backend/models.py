from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, \
    BigInteger, insert, Integer

from kgextractiontoolbox.backend import models
from kgextractiontoolbox.backend.models import Base, DatabaseTable

BULK_QUERY_CURSOR_COUNT_DEFAULT = 10000

Extended = Base


class Document(models.Document):
    pass


class DocumentClassification(models.DocumentClassification):
    pass


class Tag(models.Tag):
    pass


class TagInvertedIndex(Extended, DatabaseTable):
    __tablename__ = "tag_inverted_index"

    entity_id = Column(String, nullable=False, index=True, primary_key=True)
    entity_type = Column(String, nullable=False, index=True, primary_key=True)
    document_collection = Column(String, nullable=False, index=True, primary_key=True)
    document_ids = Column(String, nullable=False)


class Tagger(models.Tagger):
    pass


class DocTaggedBy(models.DocTaggedBy):
    pass


class DocumentTranslation(models.DocumentTranslation):
    pass


class DocumentMetadata(Extended, DatabaseTable):
    __tablename__ = 'document_metadata'
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', sqlite_on_conflict='IGNORE')
    )

    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    document_id_original = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    journals = Column(String, nullable=True)
    publication_year = Column(Integer, nullable=True)
    publication_month = Column(Integer, nullable=True)
    publication_doi = Column(String, nullable=True)


class DocumentMetadataService(Extended, DatabaseTable):
    __tablename__ = 'document_metadata_service'
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', sqlite_on_conflict='IGNORE')
    )

    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    document_id_original = Column(String, nullable=True)
    title = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    journals = Column(String, nullable=True)
    publication_year = Column(Integer, nullable=True)
    publication_month = Column(Integer, nullable=True)
    publication_doi = Column(String, nullable=True)


class Predication(models.Predication):
    pass


class PredicationInvertedIndex(Extended, DatabaseTable):
    __tablename__ = "predication_inverted_index"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), autoincrement=True, primary_key=True)
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
    def query_predication_ratings(session):
        query = session.query(PredicationRating, Predication, Sentence) \
            .filter(PredicationRating.predication_id == Predication.id) \
            .filter(Sentence.id == Predication.sentence_id)
        for res in query:
            yield res

    @staticmethod
    def query_predication_ratings_as_dicts(session):
        query = session.query(PredicationRating, Predication, Sentence) \
            .filter(PredicationRating.predication_id == Predication.id) \
            .filter(Sentence.id == Predication.sentence_id)
        for res in query:
            yield dict(document_id=res.Predication.document_id,
                       document_collection=res.Predication.document_collection,
                       rating=res.PredicationRating.rating,
                       user_id=res.PredicationRating.user_id,
                       query=res.PredicationRating.query,
                       subject_id=res.Predication.subject_id,
                       subject_type=res.Predication.subject_type,
                       subject_str=res.Predication.subject_str,
                       predicate=res.Predication.predicate,
                       relation=res.Predication.relation,
                       object_id=res.Predication.object_id,
                       object_type=res.Predication.object_type,
                       object_str=res.Predication.object_str,
                       sentence=res.Sentence.text)

    @staticmethod
    def insert_user_rating(session, user_id: str, query: str, predication_id: int, rating: str):
        insert_stmt = insert(PredicationRating).values(user_id=user_id, query=query, predication_id=predication_id,
                                                       rating=rating)
        session.execute(insert_stmt)
        session.commit()


class PredicationToDelete(models.PredicationToDelete):
    pass


class Sentence(models.Sentence):
    pass


class DocProcessedByIE(models.DocProcessedByIE):
    pass


