from sqlalchemy import Column, String, Integer, DateTime, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Document(Base):
    __tablename__ = "document"

    collection = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    abstract = Column(String, nullable=False)
    fulltext = Column(String)

    date_inserted = Column(DateTime)
    tags = relationship("Tag", backref="document")

    def __str__(self):
        return "{}{}".format(self.collection, self.id)

    def __repr__(self):
        return "<Document {}{}>".format(self.collection, self.id)


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (
        ForeignKeyConstraint(('document_id', 'document_collection'), ('document.id', 'document.collection')),
    )

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    start = Column(Integer, nullable=False)
    end = Column(Integer, nullable=False)
    ent_id = Column(String, nullable=False)
    ent_str = Column(String, nullable=False)
    document_id = Column(Integer, nullable=False)
    document_collection = Column(String, nullable=False)
    tagger = Column(String)

    def __eq__(self, other):
        return self.type == other.type and self.start == other.start and self.end == other.end and \
               self.ent_id == other.ent_id and self.ent_str == other.ent_str and \
               self.document_id == other.document_id and self.document_collection == other.document_collection

    def __hash__(self):
        return hash((self.type, self.start, self.end, self.ent_id, self.ent_str, self.document_id,
                     self.document_collection))
