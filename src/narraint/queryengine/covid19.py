import logging

from narraint.backend.database import SessionExtended
from kgextractiontoolbox.backend.models import DocumentClassification

LIT_COVID_COLLECTION = "LitCovid"
LONG_COVID_COLLECTION = "LongCovid"


def get_document_ids_for_covid19():
    """
    Gets the covid 19 relevant document ids from the PubMed collection
    :return:
    """
    session = SessionExtended.get()
    # Querying for LitCovid and Long Covid Ids
    logging.info('Querying for LitCovid document ids...')
    doc_ids_litcovid = DocumentClassification.get_document_ids_for_class(session, "PubMed", LIT_COVID_COLLECTION)
    logging.info(f'{len(doc_ids_litcovid)} document ids found')
    logging.info('Querying for LongCovid document ids...')
    doc_ids_longcovid = DocumentClassification.get_document_ids_for_class(session, "PubMed", LONG_COVID_COLLECTION)
    logging.info(f'{len(doc_ids_longcovid)} document ids found')
    return doc_ids_litcovid, doc_ids_longcovid
