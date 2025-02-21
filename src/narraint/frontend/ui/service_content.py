import json
import logging

from sqlalchemy import insert, delete
from sqlalchemy.sql.functions import func

from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, Tag, Predication, ContentData


def compute_publications_per_document_collection(session):
    # number of publications per document_collection
    # SELECT collection, count(*)
    # FROM document
    # GROUP BY collection;
    # ORDER BY count(*) DESC
    query = session.query(Document.collection, func.count())
    query = query.group_by(Document.collection)
    query = query.order_by(func.count().desc())

    collection2count = dict()
    for collection, count in query:
        collection2count[collection] = count
    return json.dumps(collection2count)


def compute_detected_entities_per_entity_type(session):
    # number of detected entities per entity type
    # SELECT ent_type, count(*)
    # FROM tag
    # WHERE count(*) >= 10000
    # GROUP BY ent_type;
    # ORDER BY count(*) DESC
    query = session.query(Tag.ent_type, func.count())
    query = query.group_by(Tag.ent_type)
    query = query.having(func.count() >= 10000)
    query = query.order_by(func.count().desc())

    entity_type2count = dict()
    for entity_type, count in query:
        entity_type2count[entity_type] = count
    return json.dumps(entity_type2count)


def compute_extracted_statements_per_relation(session):
    # number of extracted statements per relation
    # SELECT relation, count(*)
    # FROM predication
    # WHERE relation <> NULL
    # GROUP BY relation;
    # ORDER BY count(*) DESC
    session = SessionExtended.get()
    query = session.query(Predication.relation, func.count())
    query = query.filter(Predication.relation.is_not(None))
    query = query.group_by(Predication.relation)
    query = query.order_by(func.count().desc())

    relation2count = dict()
    for relation, count in query:
        relation2count[relation] = count

    return json.dumps(relation2count)


def update_content_data(session, name, data):
    session.execute(delete(ContentData).where(ContentData.name == name))
    session.execute(insert(ContentData).values(name=name, data=data))
    session.commit()


def get_content_data(name, force_update=False):
    session = SessionExtended.get()
    query = session.query(ContentData.data).filter(ContentData.name == name)
    if force_update:
        logging.info(f"Compute content data for {name}")

        if name == "collections":
            data = compute_publications_per_document_collection(session)
        elif name == "entity_types":
            data = compute_detected_entities_per_entity_type(session)
        elif name == "relations":
            data = compute_extracted_statements_per_relation(session)
        else:
            raise NotImplementedError(f"Unknown content data type: {name}")

        update_content_data(session, name, data)
        logging.info("finished update")
    elif query.count() > 0:
        data = json.loads(query.first()[0])
    else:
        data = dict()
    session.remove()
    return data


def update_content_information(force_update=False):
    content = dict()
    content["collections"] = get_content_data("collections", force_update=force_update)
    content["entity_types"] = get_content_data("entity_types", force_update=force_update)
    content["relations"] = get_content_data("relations", force_update=force_update)
    return content


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    update_content_information(force_update=True)
