import logging

from django.apps import AppConfig

from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entity.entityresolver import EntityResolver


class UiConfig(AppConfig):
    name = 'ui'
    resolver = None
    entity_tagger = None

    def ready(self):
        logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%Y-%m-%d:%H:%M:%S',
                            level=logging.DEBUG)


        logging.info('Initializing entity tagger & entity resolver once...')
        UiConfig.resolver = EntityResolver.instance()
        UiConfig.entity_tagger = EntityTagger.instance()
        logging.info('Index loaded')
