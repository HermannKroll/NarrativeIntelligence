import os
import re
import logging
import tempfile
import lxml.etree as ET

from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.vocabularies import DrugTaggerVocabulary


class DrugTagger(DictTagger):
    TYPES = (enttypes.DRUG,)
    __name__ = "DrugTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("drug", "DrugTagger", DrugTagger.__version__,
                         enttypes.DRUG, config.DRUG_TAGGER_INDEX_CACHE, config.DRUGBASE_XML_DUMP,
                         *args, **kwargs)

    def index_from_source(self):
        self.logger.info("checking total number of drugs...")
        # TODO real check
        drug_number = 13581  # subprocess.check_output(f"grep -c '^<drug' {self.source_file}")
        logging.info(f"found {drug_number}.")
        self.desc_by_term = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(self.source_file,
                                                                                        self.config.drug_min_name_length,
                                                                                        self.config.drug_check_products,
                                                                                        self.config.drug_max_per_product,
                                                                                        self.config.ignore_excipient_terms)

    def extract_dosage_forms(self):
        pref = '{http://www.drugbank.ca}'
        dosage_forms = set()
        for n, (event, elem) in enumerate(ET.iterparse(self.source_file, tag=f'{pref}dosage-form')):
            if elem.text:
                dosage_forms |= {df.lower().strip() for df in re.split(r"[,;]", elem.text)}
            if n % 10000 == 0:
                logging.info(f"at element no {n}")
        output = "\n".join(dosage_forms)
        logging.info("writing to file...")
        with open(os.path.join(config.TMP_DIR, "dosage_forms.txt"), "w+") as f:
            f.write(output)
        logging.info("done!")


def fast_iter(source_file, tag, *args, **kwargs):
    """
    http://lxml.de/parsing.html#modifying-the-tree
    Based on Liza Daly's fast_iter
    http://www.ibm.com/developerworks/xml/library/x-hiperfparse/
    See also http://effbot.org/zone/element-iterparse.htm
    """
    for event, elem in ET.iterparse(source_file, events=("start",), tag='{http://www.drugbank.ca}drug'):
        yield elem
        # It's safe to call clear() here because no descendants will be
        # accessed
        elem.clear()
        # Also eliminate now-empty references from the root node to elem
        for ancestor in elem.xpath('ancestor-or-self::*'):
            while ancestor.getprevious() is not None:
                del ancestor.getparent()[0]


if __name__ == '__main__':
    """Extract dosage forms from xml"""
    logging.basicConfig(level="INFO")
    tmpout, tmproot = tempfile.mkdtemp(), tempfile.mkdtemp()
    drt = DrugTagger(log_dir=tmpout, root_dir=tmproot)
    drt.extract_dosage_forms()
