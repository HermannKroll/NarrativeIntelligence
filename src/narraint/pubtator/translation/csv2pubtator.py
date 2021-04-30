import csv
import logging
from itertools import islice

from narrant.backend.models import Document
from narraint.pubtator.regex import PMC_ID


class CsvConverter:
    """
    Base class for converting a csv file into pubtator format
    """
    artificial_id_counter = 0

    def __init__(self, primary_index, title_index, abstract_index, id_index=None, pmcids2pmids=None, pmc_index=None):
        self.id_index = id_index
        self.title_index = title_index
        self.abstract_index = abstract_index
        self.pmcids2pmids = pmcids2pmids
        self.pmc_index = pmc_index
        self.primary_index = primary_index

    def convert(self, input_file, output_file, artificial_offset=100000000):
        """
        Converts csv file containing at least title and abstract column to pubtator format
        :param input_file: the csv file
        :param output_file: pubtator file with empty spaces for abstract if abstract is missing
        :return:
        """
        written_documents = 0
        # logging.info(' to pubtator format...')
        skipped_documents = set()
        with open(input_file, 'rt') as input_file:
            with open(output_file, 'wt') as output_file:
                reader = csv.reader(input_file)
                for row in islice(reader, 1, None):
                    create_artificial = False
                    if self.id_index:
                        if row[self.id_index]:
                            doc_id = row[self.id_index]
                        elif self.pmcids2pmids and self.pmc_index and row[self.pmc_index]:
                            doc_id = self.pmcids2pmids.get(int(PMC_ID.match(row[self.pmc_index]).group(1)))
                        else:
                            create_artificial = True
                    else:
                        create_artificial = True
                    if create_artificial or not doc_id:
                        doc_id = artificial_offset + self.artificial_id_counter
                        self.artificial_id_counter += 1
                    title = f"@{row[self.primary_index]}@ {row[self.title_index]}" if row[self.title_index] else ""
                    abstract = row[self.abstract_index]
                    if not title.strip() and not abstract.strip():
                        skipped_documents.add(doc_id)
                        continue
                    if not abstract:
                        abstract = " "
                    output_file.write(Document.create_pubtator(doc_id, title, abstract) + "\n")
                    written_documents += 1

        logging.info(
            'The following documents have been skipped (no title and no abstract): {}'.format(skipped_documents))
        logging.info('{} documents written in PubTator format'.format(written_documents))
