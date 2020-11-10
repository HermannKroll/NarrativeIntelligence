import logging
from itertools import islice

from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger, clean_vocab_word_by_split_rules
from narraint.preprocessing.tagging.drug import DrugTaggerVocabulary


class ExcipientVocabulary:

    @staticmethod
    def create_excipient_vocabulary(excipient_database=config.EXCIPIENT_TAGGER_DATABASE_FILE,
                                    drugbank_db_file=config.DRUGBASE_XML_DUMP, expand_terms_by_e_and_s=True):
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
                    if expand_terms_by_e_and_s:
                        excipient_terms = [excipient, f'{excipient}s', f'{excipient}e']
                        if excipient[-1] in ['e', 's'] and len(excipient) > 3:
                            excipient_terms.append(excipient[:-1])
                    else:
                        excipient_terms = [excipient]

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


class ExcipientTagger(DictTagger):
    TYPES = (enttypes.EXCIPIENT,)
    __name__ = "ExcipientTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("excipient", "ExcipientTagger", ExcipientTagger.__version__,
                         enttypes.EXCIPIENT, config.EXCIPIENT_TAGGER_INDEX_CACHE, config.EXCIPIENT_TAGGER_DATABASE_FILE,
                         *args, **kwargs)

    def index_from_source(self):
        self.logger.info('Reading drugbank database for DrugBank mapping...')
        self.desc_by_term = ExcipientVocabulary.create_excipient_vocabulary()

        new_excipients, drugbank_mappings_found = 0, 0
        for term, descs in self.desc_by_term.items():
            for d in descs:
                if d.startswith('DB'):
                    drugbank_mappings_found += 1
                else:
                    new_excipients += 1
        self.logger.info(
            f'{drugbank_mappings_found} excipients could be mapped to DrugBank. {new_excipients} are not in DrugBank')
        self.logger.info(f'{len(self.desc_by_term)} excipients found in database')
