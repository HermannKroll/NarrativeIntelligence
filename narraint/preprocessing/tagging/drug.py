import os
import re
import logging
import tempfile
from datetime import datetime
from itertools import islice

import lxml.etree as ET

from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger, clean_vocab_word_by_split_rules
from narraint.preprocessing.tagging.excipient import ExcipientVocabulary
from narraint.progress import print_progress_with_eta


class DrugTaggerVocabulary:


    @staticmethod
    def create_drugbank_vocabulary_from_source(source_file=config.DRUGBASE_XML_DUMP, drug_min_name_length=3,
                                               check_products=0, drug_max_per_product=2, ignore_excipient_terms=0):
        # TODO real check
        drug_number = 13581  # subprocess.check_output(f"grep -c '^<drug' {self.source_file}")
        start = datetime.now()
        drugs_found = 0
        logging.info(f"")
        pref = '{http://www.drugbank.ca}'
        desc_by_term = {}
        for event, elem in ET.iterparse(source_file, tag=f'{pref}drug'):
            desc = ''
            for dbid in elem.findall(f'{pref}drugbank-id'):
                if dbid.attrib.get('primary'):
                    desc = dbid.text
                    break
            if desc == '':
                continue
            drugs_found += 1
            print_progress_with_eta("building index...", drugs_found, drug_number, start, print_every_k=100)
            description_text = elem.find(f'{pref}description').text
            if description_text and 'allergen' in description_text.lower()[0:20]:
                continue
            name_elements = list(elem.findall(f'{pref}name'))
            synonyms = elem.find(f'{pref}synonyms')
            if synonyms is not None:
                name_elements += list(synonyms.findall(f'{pref}synonym'))
            if check_products > 0:
                products = elem.find(f'{pref}products')
                if products is not None:
                    for product in products.findall(f'{pref}product'):
                        name = product.find(f'{pref}name')
                        if name is not None:
                            name_elements.append(name)
            exp_props = elem.find(f'{pref}experimental-properties')
            if exp_props is not None:
                for exp_prop in exp_props:
                    if exp_prop.find(f'{pref}kind').text == "Molecular Formula":
                        name_elements.append(exp_prop.find(f'{pref}value'))
            names = {ne.text for ne in name_elements if len(ne.text) >= drug_min_name_length}
            names = {clean_vocab_word_by_split_rules(n.lower()) for n in names}
            names = names | {f"{n}s" for n in names} | {f"{n}e" for n in names}
            for n in names:
                if n in desc_by_term:
                    desc_by_term[n].add(desc)
                else:
                    desc_by_term[n] = {desc, }
        if drug_max_per_product > 0:
            desc_by_term = {k: v
                            for k, v in desc_by_term.items()
                            if len(v) <= drug_max_per_product}
        if ignore_excipient_terms > 0:
            excipient_terms = ExcipientVocabulary.read_excipients_names()
            desc_by_term = {k: v
                            for k, v in desc_by_term.items()
                            if k not in excipient_terms}
        return desc_by_term


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
