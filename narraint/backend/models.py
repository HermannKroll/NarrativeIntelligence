import unicodedata
from collections import namedtuple
from datetime import datetime

from sqlalchemy import Boolean, Column, String, Float, Integer, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, \
    BigInteger, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from narraint.pubtator.regex import ILLEGAL_CHAR

Base = declarative_base()


class Document(Base):
    __tablename__ = "document"
    __table_args__ = (
        PrimaryKeyConstraint('collection', 'id', sqlite_on_conflict='IGNORE'),
    )
    collection = Column(String)
    id = Column(BigInteger)
    title = Column(String, nullable=False)
    abstract = Column(String, nullable=False)
    fulltext = Column(String)

    date_inserted = Column(DateTime, nullable=False, default=datetime.now)

    def __str__(self):
        return "{}{}".format(self.collection, self.id)

    def __repr__(self):
        return "<Document {}{}>".format(self.collection, self.id)

    def to_pubtator(self):
        return Document.create_pubtator(self.title, self.abstract)

    @staticmethod
    def create_pubtator(did, title: str, abstract: str):
        title = unicodedata.normalize('NFD', title)
        title = ILLEGAL_CHAR.sub("", title).strip()
        abstract = unicodedata.normalize('NFD', abstract)
        abstract = ILLEGAL_CHAR.sub("", abstract).strip()
        return "{id}|t| {tit}\n{id}|a| {abs}\n".format(id=did, tit=title,
                                                       abs=abstract)

    @staticmethod
    def sanitize(to_sanitize):
        to_sanitize= unicodedata.normalize('NFD', to_sanitize)
        to_sanitize = ILLEGAL_CHAR.sub("", to_sanitize)
        return to_sanitize



class Tagger(Base):
    __tablename__ = "tagger"
    __table_args__ = (
        PrimaryKeyConstraint('name', 'version', sqlite_on_conflict='IGNORE'),
    )
    name = Column(String, primary_key=True)
    version = Column(String, primary_key=True)


class DocTaggedBy(Base):
    __tablename__ = "doc_tagged_by"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')
                             , sqlite_on_conflict='IGNORE'),
        ForeignKeyConstraint(('tagger_name', 'tagger_version'), ('tagger.name', 'tagger.version')
                             , sqlite_on_conflict='IGNORE'),
        PrimaryKeyConstraint('document_id', 'document_collection', 'tagger_name', 'tagger_version', 'ent_type'
                             , sqlite_on_conflict='IGNORE'),
    )
    document_id = Column(BigInteger, nullable=False, index=True)
    document_collection = Column(String, nullable=False, index=True)
    tagger_name = Column(String, nullable=False)
    tagger_version = Column(String, nullable=False)
    ent_type = Column(String, nullable=False)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection'),
                             sqlite_on_conflict='IGNORE'),
        UniqueConstraint('document_id', 'document_collection', 'start', 'end', 'ent_type', 'ent_id',
                         sqlite_on_conflict='IGNORE'),
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE')
    )

    id = Column(Integer)
    ent_type = Column(String, nullable=False)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    ent_id = Column(String, nullable=False)
    ent_str = Column(String, nullable=False)
    document_id = Column(BigInteger, nullable=False, index=True)
    document_collection = Column(String, nullable=False, index=True)
    
    def __eq__(self, other):
        return self.ent_type == other.type and self.start == other.start and self.end == other.end and \
               self.ent_id == other.ent_id and self.ent_str == other.ent_str and \
               self.document_id == other.document_id and self.document_collection == other.document_collection

    def __hash__(self):
        return hash((self.ent_type, self.start, self.end, self.ent_id, self.ent_str, self.document_id,
                     self.document_collection))

    @staticmethod
    def create_pubtator(did, start, end, ent_str, ent_type, ent_id):
        return "{}\t{}\t{}\t{}\t{}\t{}\n".format(did, start, end, ent_str, ent_type, ent_id)

    def to_pubtator(self):
        return Tag.create_pubtator(self.document_id, self.start, self.end, self.ent_str, self.ent_type, self.ent_id)


PredicationResult = namedtuple('PredicationResult', ["id", "document_id", "document_collection",
                                                     "subject_id", "subject_str", "subject_type",
                                                     "predicate", "predicate_canonicalized",
                                                     "object_id", "object_str", "object_type",
                                                     "confidence", "sentence_id", "extraction_type"])


class Predication(Base):
    __tablename__ = "predication"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        ForeignKeyConstraint(('sentence_id',), ('sentence.id',)),
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE'),
        UniqueConstraint('document_id', 'document_collection', 'subject_id', 'subject_type',
                         'predicate', 'object_id', 'object_type', 'extraction_type', 'sentence_id',
                         sqlite_on_conflict='IGNORE'),
    )

    id = Column(BigInteger, autoincrement=True)
    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    subject_str = Column(String, nullable=False)
    subject_type = Column(String, nullable=False)
    predicate = Column(String, nullable=False)
    predicate_canonicalized = Column(String, nullable=True)
    object_id = Column(String, nullable=False)
    object_str = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    sentence_id = Column(BigInteger, nullable=False)
    extraction_type = Column(String, nullable=False)

    def __str__(self):
        return "<{}>\t<{}>\t<{}>".format(self.subject_id, self.predicate, self.object_id)

    def __repr__(self):
        return "<Predication {}>".format(self.id)


class Sentence(Base):
    __tablename__ = "sentence"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('id', sqlite_on_conflict='IGNORE')
    )

    id = Column(BigInteger, autoincrement=True)
    document_id = Column(BigInteger, nullable=False, index=True)
    document_collection = Column(String, nullable=False, index=True)
    text = Column(String, nullable=False)
    md5hash = Column(String, nullable=False)


class DocProcessedByIE(Base):
    __tablename__ = "doc_processed_by_ie"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        PrimaryKeyConstraint('document_id', 'document_collection', 'extraction_type', sqlite_on_conflict='IGNORE')
    )
    document_id = Column(BigInteger)
    document_collection = Column(String)
    extraction_type = Column(String)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)


class DocumentTranslation(Base):
    __tablename__ = "document_translation"
    __table_args__ = (
        PrimaryKeyConstraint('document_id', 'document_collection', sqlite_on_conflict='IGNORE'),
    )
    document_id = Column(BigInteger)
    document_collection = Column(String)
    source_doc_id = Column(String, nullable=False)
    md5 = Column(String, nullable=False)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)
    source = Column(String)
