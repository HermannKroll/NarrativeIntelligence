from collections import defaultdict
from datetime import datetime
from typing import List, Set

from sqlalchemy import Column, String, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, \
    BigInteger, insert, Integer, and_

from kgextractiontoolbox.backend import models
from kgextractiontoolbox.backend.models import Base, DatabaseTable
from narraint.document.narrative_document import NarrativeDocument, StatementExtraction, DocumentSentence, \
    NarrativeDocumentMetadata
from narrant.pubtator.document import TaggedEntity

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


def retrieve_narrative_documents_from_database(session, document_ids: Set[int], document_collection: str) \
        -> List[NarrativeDocument]:
    """
    Retrieves a set of Narrative Documents from the database
    :param session: the current session
    :param document_ids: a set of document ids
    :param document_collection: the corresponding document collection
    :return: a list of NarrativeDocuments
    """
    doc_results = {}

    # logging.info(f'Querying {len(document_ids)} from collection: {document_collection}...')
    # first query document titles and abstract
    doc_query = session.query(Document).filter(and_(Document.id.in_(document_ids),
                                                    Document.collection == document_collection))

    for res in doc_query:
        doc_results[res.id] = NarrativeDocument(document_id=res.id, title=res.title, abstract=res.abstract)

    #   logging.info('Querying for document classification...')
    # Next query the publication information
    classification_query = session.query(DocumentClassification).filter(
        and_(DocumentClassification.document_id.in_(document_ids),
             DocumentClassification.document_collection == document_collection))
    doc2classification = defaultdict(set)
    for res in classification_query:
        doc2classification[res.document_id].add((res.classification, res.explanation))

    #    logging.info('Querying for metadata...')
    # Next query the publication information
    metadata_query = session.query(DocumentMetadata).filter(and_(DocumentMetadata.document_id.in_(document_ids),
                                                                 DocumentMetadata.document_collection == document_collection))
    doc2metadata = {}
    for res in metadata_query:
        metadata = NarrativeDocumentMetadata(publication_year=res.publication_year,
                                             publication_month=res.publication_month,
                                             authors=res.authors,
                                             journals=res.journals,
                                             publication_doi=res.publication_doi)
        doc2metadata[res.document_id] = metadata

    #  logging.info('Querying for tags...')
    # Next query for all tagged entities in that document
    tag_query = session.query(Tag).filter(and_(Tag.document_id.in_(document_ids),
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

    # logging.info('Querying for statement extractions...')
    # Next query for extracted statements
    es_query = session.query(Predication).filter(and_(Predication.document_id.in_(document_ids),
                                                      Predication.document_collection == document_collection))
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
                                                               sentence_id=res.sentence_id))

    for doc_id, extractions in es_for_doc.items():
        doc_results[doc_id].extracted_statements = extractions

    # logging.info('Querying for sentences...')
    # Last query for document sentences
    sentence_query = session.query(Sentence).filter(and_(Sentence.document_id.in_(document_ids),
                                                         Sentence.document_collection == document_collection))
    doc2sentences = defaultdict(list)
    for res in sentence_query:
        doc2sentences[res.document_id].append(DocumentSentence(sentence_id=res.id, text=res.text))

    for doc_id, sentences in doc2sentences.items():
        doc_results[doc_id].sentences = sentences

    for doc_id, metadata in doc2metadata.items():
        doc_results[doc_id].metadata = metadata

    for doc_id, classification in doc2classification.items():
        doc_results[doc_id].classification = {d_class: d_expl for d_class, d_expl in classification}

    return list(doc_results.values())
