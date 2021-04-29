import logging
import os
import shutil
import tempfile

from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.collect import PMCCollector
from narraint.preprocessing.config import Config
from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
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
    logging.info('Load PMCID to PMID translation file')
    pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)
    pmid2pmcid = {v: k for k, v in pmcid2pmid.items()}
    pmcid_doc_ids = set()
    for doc_id in doc_ids:
        if doc_id in pmid2pmcid:
            pmcid_doc_ids.add('PMC{}'.format(pmid2pmcid[doc_id]))
    logging.info('{} of {} have a correct PMCID...'.format(len(pmcid_doc_ids), len(doc_ids)))
    if pmcid_doc_ids:
        error_file = os.path.join(tmp_dir, "conversion_errors.txt")
        collector = PMCCollector(conf.pmc_dir)
        files = collector.collect(pmcid_doc_ids)
        if files:
            logging.info('{} matching nxml files found ({} of {})'.format(len(files), len(files), len(doc_ids)))
            translator = PMCConverter()
            translator.convert_bulk(files, tmp_dir_pmc_files, pmcid2pmid, error_file)

            enrich_pubtator_documents_with_database_tags(tmp_dir_pmc_files, out_fn, 'PMC', tag_types)
    shutil.rmtree(tmp_dir)
    logging.info('export to {} finished -- temp directory {} removed'.format(out_fn, tmp_dir))

