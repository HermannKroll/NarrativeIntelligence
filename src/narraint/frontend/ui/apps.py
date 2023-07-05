import logging

from django.apps import AppConfig

from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entity.entityresolver import EntityResolver
from narraint.logging_config import configure_logging

class UiConfig(AppConfig):
    name = 'ui'
    resolver = None
    entity_tagger = None

    def ready(self):
        configure_logging()
        logging.info('Initializing entity tagger & entity resolver once...')
        UiConfig.resolver = EntityResolver.instance()
        UiConfig.entity_tagger = EntityTagger.instance()
        logging.info('Index loaded')
