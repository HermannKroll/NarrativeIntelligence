import logging
import os
import shutil
import tempfile

from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.collect import PMCCollector
from narraint.preprocessing.config import Config
from narraint.pubtator.enrich_docs_with_tags import enrich_pubtator_documents_with_database_tags
from narraint.pubtator.translation.pmc import PMCConverter


def export_pmc_fulltexts_with_tags(out_fn, tag_types, doc_ids):
    """
    Exports PMC Fulltext files enriched with database tags
    1. The PMC files are searched in the PMC dump and extracted
    2. Tags in the DB are queried and added to the documents
    :param out_fn: the resulting PubTator file will be stored here
    :param tag_types: tag types to export
    :param doc_ids: a set of PMID document ids
    :return: None
    """
    conf = Config(PREPROCESS_CONFIG)
    tmp_dir = tempfile.mkdtemp()
    tmp_dir_pmc_files = os.path.join(tmp_dir, 'pmc')
    os.mkdir(tmp_dir_pmc_files)
    logging.info('working in temp directory: {}'.format(tmp_dir))

    error_file = os.path.join(tmp_dir, "conversion_errors.txt")
    collector = PMCCollector(conf.pmc_dir)
    files = collector.collect(doc_ids)
    translator = PMCConverter()
    translator.convert_bulk(files, tmp_dir_pmc_files, {}, error_file)

    enrich_pubtator_documents_with_database_tags(tmp_dir_pmc_files, out_fn, 'PMC', tag_types)
    shutil.rmtree(tmp_dir)
    logging.info('export to {} finished.temp directory {} removed'.format(out_fn, tmp_dir))

