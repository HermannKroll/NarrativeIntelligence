from collections import defaultdict
from sqlalchemy import and_

from kgextractiontoolbox.backend.models import Predication
from kgextractiontoolbox.document.document import TaggedEntity
from kgextractiontoolbox.document.narrative_document import NarrativeDocument, StatementExtraction
from narraint.backend.models import Tag


def load_document_entities_and_statements_from_db(session, documents: [NarrativeDocument], document_collection: str):
    document_ids = set([d.id for d in documents])
    docid2doc = {d.id: d for d in documents}

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
        docid2doc[doc_id].tags = tags
        docid2doc[doc_id].sort_tags()

    # Next query for extracted statements
    es_query = session.query(Predication)
    es_query = es_query.filter(Predication.document_collection == document_collection)
    es_query = es_query.filter(Predication.document_id.in_(document_ids))
    es_query = es_query.filter(Predication.relation != None)

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
                                                               sentence_id=res.sentence_id,
                                                               confidence=res.confidence))
        sentence_ids.add(res.sentence_id)
        sentenceid2doc[res.sentence_id].add(res.document_id)

    for doc_id, extractions in es_for_doc.items():
        docid2doc[doc_id].extracted_statements = extractions
