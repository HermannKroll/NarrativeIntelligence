import argparse

import logging

from sqlalchemy import and_

from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, DocTaggedBy, Tag
from narrant.preprocessing.enttypes import PLANT_FAMILY, DRUG, SPECIES, GENE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("idfile", help="Document ID file (documents must be in database)")
    parser.add_argument("-c", "--collection", required=True, help="Document collection")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    collection = args.collection

    logging.info('Querying relevant document ids...')
    session = SessionExtended.get()
    subquery = session.query(Tag.document_id).filter(and_(Tag.document_collection == collection,
                                                          Tag.ent_type.in_([DRUG, PLANT_FAMILY]))).distinct()
    subquery2 = session.query(Tag.document_id).filter(and_(Tag.document_collection == collection,
                                                           Tag.ent_type.in_([GENE, SPECIES]))).distinct()
    query = session.query(Document.id).filter(Document.collection == collection).filter(and_(Document.id.in_(subquery),
                                                                                             Document.id.notin_(
                                                                                                 subquery2)))

    logging.info('Collecting document ids...')
    document_ids = set()
    for r in query:
        document_ids.add(int(r[0]))

    logging.info(f'Writing {len(document_ids)} to file {args.idfile}...')
    with open(args.idfile, 'wt') as f:
        f.write('\n'.join([str(d) for d in document_ids]))
    logging.info('Finished')


if __name__ == "__main__":
    main()
