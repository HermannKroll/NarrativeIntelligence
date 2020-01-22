from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKeyConstraint, PrimaryKeyConstraint, BigInteger, \
    UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

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
    def create_pubtator(did, title, abstract):
        return "{id}|t| {tit}\n{id}|a| {abs}\n".format(id=did, tit=title, abs=abstract)


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
        # Todo: think about these constraints
        #       ForeignKeyConstraint(('document_id', 'document_collection', 'tagger_name', 'tagger_version', 'ent_type'),
        #                            ('doc_tagged_by.document_id', 'doc_tagged_by.collection', 'doc_tagged_by.tagger_name',
        #                             'doc_tagged_by.tagger_version', 'doc_tagged_by.ent_type')),
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
