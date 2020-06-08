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

    collection = Column(String, primary_key=True)
    id = Column(BigInteger, primary_key=True)
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


class Tagger(Base):
    __tablename__ = "tagger"
    name = Column(String, primary_key=True)
    version = Column(String, primary_key=True)


class DocTaggedBy(Base):
    __tablename__ = "doc_tagged_by"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        ForeignKeyConstraint(('tagger_name', 'tagger_version'), ('tagger.name', 'tagger.version')),
        PrimaryKeyConstraint('document_id', 'document_collection', 'tagger_name', 'tagger_version', 'ent_type'),
    )
    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    tagger_name = Column(String, nullable=False)
    tagger_version = Column(String, nullable=False)
    ent_type = Column(String, nullable=False)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
        ForeignKeyConstraint(('tagger_name', 'tagger_version'), ('tagger.name', 'tagger.version')),
        UniqueConstraint('document_id', 'document_collection', 'start', 'end', 'ent_type', 'ent_id'),
    )

    id = Column(Integer, primary_key=True)
    ent_type = Column(String, nullable=False)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    ent_id = Column(String, nullable=False)
    ent_str = Column(String, nullable=False)
    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    tagger_name = Column(String, nullable=False)
    tagger_version = Column(String, nullable=False)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)

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
                                                     "subject_openie", "subject_id", "subject_str", "subject_type",
                                                     "predicate", "predicate_cleaned", "predicate_canonicalized",
                                                     "object_openie", "object_id", "object_str", "object_type",
                                                     "confidence", "sentence", "extraction_type", "extraction_version",
                                                     "mirrored",  "date_inserted"])


class Predication(Base):
    __tablename__ = "predication"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, nullable=False)
    document_collection = Column(String, nullable=False)
    subject_openie = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    subject_str = Column(String, nullable=False)
    subject_type = Column(String, nullable=False)
    predicate = Column(String, nullable=False)
    predicate_cleaned = Column(String, nullable=True)
    predicate_canonicalized = Column(String, nullable=True)
    object_openie = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_str = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=True)
    sentence = Column(String, nullable=False)
    extraction_type = Column(String, nullable=False)
    extraction_version = Column(String, nullable=False)
    mirrored = Column(Boolean, nullable=False, default=False)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)

    def __str__(self):
        return "<{}>\t<{}>\t<{}>".format(self.subject_id, self.predicate, self.object_id)

    def __repr__(self):
        return "<Predication {}>".format(self.id)


class DocProcessedByOpenIE(Base):
    __tablename__ = "doc_processed_by_openie"

    document_id = Column(BigInteger, primary_key=True)
    document_collection = Column(String, primary_key=True)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)


class DocumentTranslation(Base):
    __tablename__ = "cord19_translation"
    document_id = Column(BigInteger, primary_key=True)
    document_collection = Column(String, primary_key=True)
    source_doc_id = Column(String, nullable=False)
    md5 = Column(String, nullable=False)
    date_inserted = Column(DateTime, nullable=False, default=datetime.now)
