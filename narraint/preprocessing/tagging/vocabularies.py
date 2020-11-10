import logging
from datetime import datetime
from itertools import islice
import lxml.etree as ET

from narraint import config
from narraint.preprocessing.tagging.dictagger import clean_vocab_word_by_split_rules
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


class ExcipientVocabulary:

    @staticmethod
    def read_excipients_names(source_file=config.EXCIPIENT_TAGGER_DATABASE_FILE, expand_terms_by_e_and_s=True):
        excipient_terms = set()
        with open(source_file, 'rt') as f:
            for line in islice(f, 1, None):
                comps = line.split('~')
                excipient = clean_vocab_word_by_split_rules(comps[0].strip().lower())
                if len(excipient) > 2:
                    if expand_terms_by_e_and_s:
                        excipient_terms.update([excipient, f'{excipient}s', f'{excipient}e'])
                        if excipient[-1] in ['e', 's'] and len(excipient) > 3:
                            excipient_terms.add(excipient[:-1])
                    else:
                        excipient_terms.add(excipient)
        return excipient_terms

    @staticmethod
    def create_excipient_vocabulary(excipient_database=config.EXCIPIENT_TAGGER_DATABASE_FILE,
                                    drugbank_db_file=config.DRUGBASE_XML_DUMP, ):
        # we cannot ignore the excipient terms while reading drugbank here (else our mapping would be empty)
        drugbank_terms = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(source_file=drugbank_db_file,
                                                                                     ignore_excipient_terms=0)
        logging.info(f'Reading excipient database: {excipient_database}...')
        desc_by_term = {}
        with open(excipient_database, 'rt') as f:
            drugbank_mappings_found = 0
            new_excipients = 0
            for line in islice(f, 1, None):
                comps = line.split('~')
                excipient = clean_vocab_word_by_split_rules(comps[0].strip().lower())
                excipient_heading = excipient.capitalize()
                if len(excipient) > 2:
                    excipient_terms = [excipient, f'{excipient}s', f'{excipient}e']
                    if excipient[-1] in ['e', 's'] and len(excipient) > 3:
                        excipient_terms.append(excipient[:-1])
                    drugbank_mapping = set()
                    for term in excipient_terms:
                        if term in drugbank_terms:
                            drugbank_mapping.update(drugbank_terms[term])
                    if len(drugbank_mapping) > 0:
                        drugbank_mappings_found += 1
                        for term in excipient_terms:
                            desc_by_term[term] = list(drugbank_mapping)
                    else:
                        new_excipients += 1
                        for term in excipient_terms:
                            desc_by_term[term] = list([excipient_heading])
        return desc_by_term
