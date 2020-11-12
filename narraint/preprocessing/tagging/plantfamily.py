from narraint import config
from narraint.entity import enttypes
from narraint.preprocessing.tagging.dictagger import DictTagger
from narraint.preprocessing.tagging.vocabularies import PlantFamilyVocabulary


class PlantFamilyTagger(DictTagger):
    TYPES = (enttypes.EXCIPIENT,)
    __name__ = "PlantFamilyTagger"
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__("plantfamily", "PlantFamilyTagger", PlantFamilyTagger.__version__,
                         enttypes.PLANTFAMILY, config.PLANT_FAMILTY_INDEX_CACHE, config.PLANT_FAMILTY_DATABASE_FILE,
                         *args, **kwargs)

    def index_from_source(self):
        self.logger.info('Creating dictionary from source...')
        self.desc_by_term = PlantFamilyVocabulary.read_plant_family_vocabulary(self.source_file)
        self.logger.info(f'{len(self.desc_by_term)} Plant Families found in database')
