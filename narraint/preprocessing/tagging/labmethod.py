from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.vocabularies import MethodVocabulary, LabMethodVocabulary


class LabMethodTagger(DictTagger):
    TYPES = (enttypes.METHOD,)
    __name__ = "LabMethodTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("labmethod", "LabMethodTagger", LabMethodTagger.__version__,
                         enttypes.LAB_METHOD, config.LAB_METHOD_TAGGER_INDEX_CACHE, config.METHOD_TAGGER_DATABASE_FILE,
                         *args, **kwargs)

    def _index_from_source(self):
        self.logger.info('Creating dictionary from source...')
        self.desc_by_term = LabMethodVocabulary.create_lab_method_vocabulary(self.source_file)
        self.logger.info(f'{len(self.desc_by_term)} Lab Method terms found in database')
