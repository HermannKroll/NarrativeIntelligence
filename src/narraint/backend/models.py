from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, \
    BigInteger, insert, Integer, Date, delete

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
    support = Column(Integer, nullable=False)
    document_ids = Column(String, nullable=False)


class TermInvertedIndex(Extended, DatabaseTable):
    __tablename__ = "term_inverted_index"

    term = Column(String, nullable=False, index=True, primary_key=True)
    document_collection = Column(String, nullable=False, index=True, primary_key=True)
    document_ids = Column(String, nullable=False)


class Tagger(models.Tagger):
    pass


class DocTaggedBy(models.DocTaggedBy):
    pass


class DocumentTranslation(models.DocumentTranslation):
    pass


class DocumentMetadata(models.DocumentMetadata):
    pass


class DocumentMetadataService(Extended, DatabaseTable):
    __tablename__ = 'document_metadata_service'
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', sqlite_on_conflict='IGNORE')
    )

    document_id = Column(BigInteger, nullable=False, index=True)
    document_collection = Column(String, nullable=False, index=True)
    document_id_original = Column(String, nullable=True)
    title = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    journals = Column(String, nullable=True)
    publication_year = Column(Integer, nullable=True)
    publication_month = Column(Integer, nullable=True)
    publication_doi = Column(String, nullable=True)
    document_classifications = Column(String, nullable=True)


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


class SubstitutionGroupRating(Extended, DatabaseTable):
    __tablename__ = "substitution_group_rating"
    variable_name = Column(String, primary_key=True)
    entity_name = Column(String, primary_key=True)
    entity_id = Column(String, primary_key=True)
    entity_type = Column(String, primary_key=True)
    user_id = Column(String, primary_key=True)
    query = Column(String, primary_key=True)
    rating = Column(String)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)

    @staticmethod
    def insert_sub_group_user_rating(
            session, user_id: str, query: str, variable_name: str,
            entity_name: str, entity_id: str, entity_type: str, rating: str):
        insert_stmt = insert(SubstitutionGroupRating).values(
            user_id=user_id, query=query, variable_name=variable_name,
            entity_name=entity_name, entity_id=entity_id,
            entity_type=entity_type, rating=rating)
        session.execute(insert_stmt)
        session.commit()

    @staticmethod
    def query_subgroup_ratings_as_dicts(session):
        query = session.query(SubstitutionGroupRating)
        if not query:
            return dict()
        for res in query:
            yield dict(variable_name=res.variable_name,
                       entity_name=res.entity_name,
                       entity_id=res.entity_id,
                       entity_type=res.entity_type,
                       query=res.query,
                       user_id=res.user_id,
                       rating=res.rating)


class EntityKeywords(Extended, DatabaseTable):
    __tablename__ = "entity_keywords"
    entity_id = Column(String, nullable=False, primary_key=True)
    entity_type = Column(String, nullable=False)
    keyword_data = Column(String, nullable=False)

    @staticmethod
    def insert_entity_keyword_data(session, entity_id: str, entity_type: str, keyword_data: str):
        insert_stmt = insert(EntityKeywords).values(entity_id=entity_id, entity_type=entity_type,
                                                    keyword_data=keyword_data)
        session.execute(insert_stmt)
        session.commit()


class SchemaSupportGraphInfo(Extended, DatabaseTable):
    __tablename__ = "schema_support_graph_info"

    subject_type = Column(String, nullable=False, primary_key=True)
    relation = Column(String, nullable=False, primary_key=True)
    object_type = Column(String, nullable=False, primary_key=True)
    support = Column(Integer, nullable=False)


class DrugDiseaseTrialPhase(Extended, DatabaseTable):
    __tablename__ = "drug_disease_trial_phase"

    drug = Column(String, primary_key=True)
    disease = Column(String, primary_key=True)
    phase = Column(Integer, nullable=False)


class DatabaseUpdate(Extended, DatabaseTable):
    __tablename__ = "database_update"

    last_update = Column(Date, primary_key=True)

    @staticmethod
    def get_latest_update(session):
        dates = []
        for date in session.query(DatabaseUpdate):
            dates.append(date.last_update)

        if len(dates) == 0:
            raise ValueError('There are not update dates in the database')

        dates.sort(reverse=True)
        return dates[0]

    @staticmethod
    def update_date_to_now(session):
        delete_stmt = delete(DatabaseUpdate)
        session.execute(delete_stmt)

        insert_stmt = insert(DatabaseUpdate).values(last_update=datetime.now())
        session.execute(insert_stmt)
        session.commit()
