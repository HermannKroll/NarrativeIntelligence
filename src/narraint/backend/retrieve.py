from collections import defaultdict
from typing import Set, List

from sqlalchemy import and_

from kgextractiontoolbox.backend.models import DocumentSection
from kgextractiontoolbox.document.document import DocumentSection as ds
from kgextractiontoolbox.document.document import TaggedEntity
from narraint.backend.models import Document, DocumentClassification, DocumentMetadata, Tag, Predication, Sentence
from narraint.document.narrative_document import NarrativeDocument, NarrativeDocumentMetadata, StatementExtraction, \
    DocumentSentence


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

    # Query for Document sections
    sec_query = session.query(DocumentSection).filter(and_(DocumentSection.document_id.in_(document_ids),
                                                           DocumentSection.document_collection == document_collection))
    for res_sec in sec_query:
        doc_results[res_sec.document_id].sections.append(ds(
            position=res_sec.position,
            title=res_sec.title,
            text=res_sec.text
        ))
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
    sentence_ids = set()
    sentenceid2doc = defaultdict(set)
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
        sentence_ids.add(res.sentence_id)
        sentenceid2doc[res.sentence_id].add(res.document_id)

    for doc_id, extractions in es_for_doc.items():
        doc_results[doc_id].extracted_statements = extractions

    # logging.info('Querying for sentences...')
    # Last query for document sentences
    sentence_query = session.query(Sentence).filter(Sentence.id.in_(sentence_ids))
    doc2sentences = defaultdict(list)
    for res in sentence_query:
        for doc_id in sentenceid2doc[res.sentence_id]:
            doc2sentences[doc_id].append(DocumentSentence(sentence_id=res.id, text=res.text))

    for doc_id, sentences in doc2sentences.items():
        doc_results[doc_id].sentences = sentences

    for doc_id, metadata in doc2metadata.items():
        doc_results[doc_id].metadata = metadata

    for doc_id, classification in doc2classification.items():
        doc_results[doc_id].classification = {d_class: d_expl for d_class, d_expl in classification}

    return list(doc_results.values())
