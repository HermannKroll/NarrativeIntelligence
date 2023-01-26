import argparse
import json
import logging

from kgextractiontoolbox.backend.models import Tag
from narraint.backend.database import SessionExtended
from narraint.backend.retrieve import retrieve_narrative_documents_from_database


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    args = parser.parse_args(args)

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    logging.info('Retrieving document ids that have a Arabidopsis Gene...')

    session = SessionExtended.get()
    query = session.query(Tag.document_id)
    query = query.filter(Tag.document_collection == 'PubMed')
    query = query.filter(Tag.ent_type == 'ArabidopsisGene')
    document_ids = set()
    for r in query:
        document_ids.add(int(r[0]))

    logging.info(f'{len(document_ids)} relevant document ids found')
    logging.info('Beginning export...')
    narrative_docs = retrieve_narrative_documents_from_database(session=session, document_ids=document_ids,
                                                                document_collection='PubMed')

    with open(args.output, 'wt') as f:
        for doc in narrative_docs:
            doc_json = json.dumps(doc.to_dict())
            f.write(doc_json + '\n')

    logging.info('Finished')


if __name__ == "__main__":
    main()
