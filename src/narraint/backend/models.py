from datetime import datetime

from sqlalchemy import Column, String, ForeignKeyConstraint, PrimaryKeyConstraint, \
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


class PredicationInvertedIndex(Extended, DatabaseTable):
    __tablename__ = "predication_inverted_index"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), autoincrement=True, primary_key=True)
    document_collection = Column(String, nullable=False, index=True)
    subject_id = Column(String, nullable=False, index=True)
    subject_type = Column(String, nullable=False, index=True)
    relation = Column(String, nullable=False, index=True)
    object_id = Column(String, nullable=False, index=True)
    object_type = Column(String, nullable=False, index=True)
    support = Column(Integer, nullable=False)
    document_ids = Column(String, nullable=False)

    @staticmethod
    def prepare_document_ids(document_ids_str: str):
        return list(int(doc_id) for doc_id in document_ids_str.strip("[]").split(","))



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
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection'), ondelete="CASCADE"),
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


class PredicationToDelete(models.PredicationToDelete):
    pass


class Sentence(models.Sentence):
    pass


class DocProcessedByIE(models.DocProcessedByIE):
    pass


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
