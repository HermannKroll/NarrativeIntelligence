import logging
import os
from argparse import ArgumentParser
from datetime import datetime
from typing import Set, Dict, List

from lxml import etree

from narraint.backend.database import SessionExtended
from narraint.backend.models import DocumentMetadata
from narrant.backend.models import Document
from narrant.progress import print_progress_with_eta


def pubmed_medline_load_document_metadata(filename: str, document_ids: Set[int], document_collection: str) \
        -> (List[Dict], Set[int]):
    """
    Extracts the PubMed Medline Metadata from an xml file
    Authors, Journals and Publication Year
    :param filename: an PubMed Medline xml file
    :param document_ids: a set of relevant document ids
    :param document_collection: the corresponding document collection
    :return: A list of dictionaries corresponding to DocumentMetadata, a list of processed document ids
    """
    with open(filename) as f:
        tree = etree.parse(f)

    metadata_to_insert = []
    pmids_processed = set()
    for article in tree.iterfind("PubmedArticle"):

        # Get PMID
        pmids = article.findall("./MedlineCitation/PMID")
        if len(pmids) > 1:
            logging.warning(f"PubMed citation has more than one PMID {pmids}")
            continue  # BAD

        pmid = int(pmids[0].text)
        if pmid not in document_ids or pmid in pmids_processed:
            continue

        pmids_processed.add(pmid)
        authors_list = []
        for author in article.findall('./MedlineCitation/Article/AuthorList/Author'):
            forename = author.findall('./ForeName')
            lastname = author.findall('./LastName')
            # check if only one forename and lastname is entered
            if len(forename) != 1 or len(lastname) != 1:
                continue
            authors_list.append(f'{lastname[0].text}, {forename[0].text[0]}')

        if len(authors_list) < 3:
            authors = ' | '.join(authors_list)
        else:
            authors = ' | '.join(authors_list[0:3]) + ' | et al.'

        journal_list = []
        publication_year = None
        for journal in article.findall('./MedlineCitation/Article/Journal'):
            journal_elem_title = journal.findall('./Title')
            journal_elem_year = journal.findall('./JournalIssue/PubDate/Year')
            journal_elem_month = journal.findall('./JournalIssue/PubDate/Month')
            journal_elem_volume = journal.findall('./JournalIssue/Volume')
            journal_elem_issue = journal.findall('./JournalIssue/Issue')

            journal_title = journal_elem_title[0].text if len(journal_elem_title) else ""
            journal_year = journal_elem_year[0].text if len(journal_elem_year) else None
            journal_month = journal_elem_month[0].text if len(journal_elem_month) else None
            journal_volume = journal_elem_volume[0].text if len(journal_elem_volume) else ""
            journal_issue = journal_elem_issue[0].text if len(journal_elem_issue) else ""
            journal_list.append(
                f'{journal_title}, Vol. {journal_volume} No. {journal_issue} ({journal_month} {journal_year})')
            if journal_year and (not publication_year or publication_year < journal_year):
                publication_year = journal_year

        journals = ' | '.join(journal_list)

        if authors or journals or publication_year:
            metadata_to_insert.append(dict(document_id=pmid, document_collection=document_collection,
                 authors=authors, journals=journals, publication_year=publication_year))
    return metadata_to_insert, pmids_processed


def pubmed_medline_load_metadata_from_dictionary(directory, document_collection='PubMed'):
    """
    Loads a whole folder containing PubMed Medline XML files into the database
    Extracts all relevant metadata and inserts it
    Only loads metadata for documents that have no metadata in the db and that are available in the document table
    :param directory: PubMed Medline XML file directory
    :param document_collection: the document collection to insert
    :return: None
    """
    session = SessionExtended.get()
    logging.info(f'Querying document ids for collection {document_collection}...')
    d_query = session.query(Document.id).filter(Document.collection == document_collection)
    document_ids = set([d[0] for d in d_query])
    logging.info(f'{len(document_ids)} retrieved')

    logging.info(f'Querying documents that have metadata already...')
    d2_query = session.query(DocumentMetadata.document_id)\
        .filter(DocumentMetadata.document_collection == document_collection)
    document_id_processed = set([d[0] for d in d2_query])
    logging.info(f'{len(document_id_processed)} documents have already metadata...')
    document_ids = document_ids - document_id_processed
    logging.info(f'{len(document_ids)} document ids remaining...')
    files = [os.path.join(directory, fn) for fn in os.listdir(directory) if fn.endswith(".xml")]
    start = datetime.now()
    for idx, fn in enumerate(files):
        print_progress_with_eta("Loading PubMed Medline metadata", idx, len(files), start, 1)
        metadata_to_insert, pmids_processed = pubmed_medline_load_document_metadata(fn, document_ids, document_collection)
        DocumentMetadata.bulk_insert_values_into_table(session, metadata_to_insert)
        document_ids = document_ids - pmids_processed


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="PubMed Medline Directory containing all xml files")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info(f'Loading PubMed Medline metadata from {args.input}...')
    pubmed_medline_load_metadata_from_dictionary(args.input)


if __name__ == "__main__":
    main()
