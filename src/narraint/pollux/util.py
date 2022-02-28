from typing import List, Iterator, Optional

from sqlalchemy.engine import Row, ChunkedIteratorResult

from kgextractiontoolbox.backend.models import Predication
from kgextractiontoolbox.document.document import TaggedDocument, TaggedEntity
from narraint.backend.database import Session

#TODO: Implement if needed
def tagged_documents_from_database(session: Session, collection: str=None, doc_ids: List[int]=None):
    pass


def tagged_document_from_iterjoin(joined_row:List[List[Row]]) -> TaggedDocument:
    doc = joined_row[0][0][0]
    output = TaggedDocument(id=doc.id, title=doc.title, abstract=doc.abstract)
    for t in joined_row[1]:
        pass
        output.tags.append(TaggedEntity(
            document=t[0].id,
            start=t[0].start,
            end=t[0].end,
            text=t[0].ent_str,
            ent_type=t[0].ent_type,
            ent_id=t[0].ent_id
        ))
    return output

#TODO: Unittest
def iter_join(pk_query: ChunkedIteratorResult, primary_keys: List[str], fk_queries: List[Iterator[ChunkedIteratorResult]], foreign_keys:List[List[str]]) -> List[List[List[Row]]]:
    """
    iteratively join one or more tables with foreign keys to the table with the corresponding primary keys.
    Assumes, that the fk-tables are sorted by the foreign keys.
    The query iterators are expexted to be the return values of calls like session.execute(session.query(<Table>))

    :param pk_query: query iterator for the table containing the corresponding primary keys
    :param primary_keys: List of the primary key names as in database table, e.g. ['id', 'collection']
    :param fk_queries: a list of query iterators for the tables with the foreign keys that should be joined
    :param foreign_keys: list of lists of the foreign key names in the fk_queries to join on. Must be in the same order as fk_queries, e.g.[['document_id', 'document_collection'], ['document_id', 'document_collection']]
    :return: a list of joined rows. Each entry is a List containing a list for each table filled with all the rows matching the pk of the pk entry
    """
    current_key_values = []

    current_values: List[Optional[Row]] = [next(it, None) for it in fk_queries]
    pk_values = next(pk_query, None)

    while pk_values:
        current_result =[[] for _ in range(len(fk_queries)+1)]

        current_key_values = [pk_values[0].__dict__[k] for k in primary_keys]
        current_result[0].append(pk_values)
        pk_values = next(pk_query, None)

        for n, it in enumerate(fk_queries):
            while current_values[n] and key_match(foreign_keys[n], current_key_values, current_values[n]):
                current_result[n+1].append(current_values[n])
                current_values[n] = next(it, None)

        yield current_result


def key_match(join_keys: List[str], key_values:List, row:Row):
    return all([key_values[n] == row[0].__dict__[join_keys[n]] for n, val in enumerate(join_keys)])


if __name__ == '__main__':
    from kgextractiontoolbox.document.export import create_document_query, create_tag_query
    from narraint.backend.database import SessionExtended
    ses = SessionExtended.get()
    doc_query = ses.execute(create_document_query(ses, collection="pollux"))
    tag_query = ses.execute(create_tag_query(ses, collection="pollux"))
    pred_query = ses.execute(ses.query(Predication).yield_per(10_000).order_by(Predication.document_collection, Predication.document_id))
    result = []
    for r in iter_join(doc_query, ["id", "collection"], [tag_query, pred_query], [["document_id", "document_collection"],
                                                                                  ["document_id", "document_collection"]]):
        result.append(r)
        print(r)
    pass
