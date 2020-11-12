from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.vocabularies import DrugBankChemicalVocabulary


class DrugBankChemicalTagger(DictTagger):
    TYPES = (enttypes.DRUGBANKCHEMICAL,)
    __name__ = "DrugBankChemicalTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("drugbankchemical", "DrugBankChemicalTagger", DrugBankChemicalTagger.__version__,
                         enttypes.DRUGBANKCHEMICAL, config.DRUGBANK_CHEMICAL_INDEX_CACHE, config.DRUGBANK_CHEMICAL_DATABASE_FILE,
                         *args, **kwargs)

    def index_from_source(self):
        self.logger.info('Creating dictionary from source...')
        self.desc_by_term = DrugBankChemicalVocabulary.create_drugbank_chemical_vocabulary(drugbank_chemical_list=self.source_file)
        self.logger.info(f'{len(self.desc_by_term)} DrugBank chemicals found in database')
