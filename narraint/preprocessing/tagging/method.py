from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.vocabularies import MethodVocabulary


class MethodTagger(DictTagger):
    TYPES = (enttypes.METHOD,)
    __name__ = "MethodTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("method", "MethodTagger", MethodTagger.__version__,
                         enttypes.METHOD, config.METHOD_TAGGER_INDEX_CACHE, config.METHOD_TAGGER_DATABASE_FILE,
                         *args, **kwargs)

    def _index_from_source(self):
        self.logger.info('Creating dictionary from source...')
        self.desc_by_term = MethodVocabulary.create_method_vocabulary(self.source_file)
        self.logger.info(f'{len(self.desc_by_term)} Method terms found in database')
