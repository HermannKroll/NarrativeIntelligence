from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.vocabularies import DiseaseVocabulary


class DiseaseTagger(DictTagger):
    TYPES = (enttypes.DISEASE,)
    __name__ = "DiseaseTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("disease", "DiseaseTagger", DiseaseTagger.__version__,
                         enttypes.DISEASE, config.DISEASE_TAGGER_INDEX_CACHE, config.DISEASE_TAGGER_DATABASE_FILE,
                         *args, **kwargs)

    def _index_from_source(self):
        self.logger.info('Creating dictionary from source...')
        self.desc_by_term = DiseaseVocabulary.create_disease_vocabulary(self.source_file)
        self.logger.info(f'{len(self.desc_by_term)} Disease terms found in database')
