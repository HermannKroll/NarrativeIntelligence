import logging
import pickle
import string
from collections import defaultdict
from typing import Set

from narraint.frontend.entity.entityindexbase import EntityIndexBase
from narraint.config import ENTITY_TAGGING_INDEX
from narrant.entity.entity import Entity


class EntityTagger(EntityIndexBase):
    """
    EntityTagger converts a string to an entity
    Performs a simple dictionary-based lookup and returns the corresponding entity
    Builds upon the EntityResolver and computes reverse indexes,
    e.g. Gene_ID -> Gene_Name is converted to Gene_Name -> Gene_ID
    """
    __instance = None

    VERSION = 5
    LOAD_INDEX = True

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            logging.info('Initialize EntityTagger...')
            cls.__instance.autocompletion = None
            cls.__instance.term2entity = defaultdict(set)
            cls.__instance.known_terms = set()

            trans_map = {p: '' for p in string.punctuation}
            # necessary to not distinguish between
            # "Axicabtagene Ciloleucel"
            # "Axicabtagene-Ciloleucel"
            # "AxicabtageneCiloleucel"
            trans_map[' '] = ''
            cls.__instance.__translator = str.maketrans(trans_map)
            cls.__instance.version = None
            if EntityTagger.LOAD_INDEX:
                try:
                    cls.__instance._load_index()
                except ValueError:
                    logging.info('Index is outdated. Creating a new one...')
                    # The index has been outdated or is old - create a new one
                    cls.__instance.store_index()
        return cls.__instance

    def _load_index(self, index_path=ENTITY_TAGGING_INDEX):
        logging.info(f'Loading entity tagging index from {index_path}')
        with open(index_path, 'rb') as f:
            self.version, self.known_terms, self.term2entity = pickle.load(f)

            if self.version != EntityTagger.VERSION:
                raise ValueError('Entitytagging index is outdated.')

        logging.info(f'Index load ({len(self.term2entity)} different terms)')

    def store_index(self, index_path=ENTITY_TAGGING_INDEX):
        self.version = EntityTagger.VERSION
        logging.info('Computing entity tagging index...')
        self._create_index()
        logging.info('{} different terms map to entities'.format(len(self.term2entity)))
        logging.info(f'Storing index to {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump((self.version, self.known_terms, self.term2entity), f)
        logging.info('Index stored')

    def _add_term(self, term, entity_id: str, entity_type: str, entity_class: str = None):
        term_lower = term.strip().lower()
        self.known_terms.add(term_lower)

        term_wo_punctuation = term_lower.translate(self.__translator).strip()
        self.term2entity[term_wo_punctuation].add(Entity(entity_id=entity_id, entity_type=entity_type,
                                                         entity_class=entity_class))

    def __find_entities(self, term: str) -> Set[Entity]:
        if term not in self.term2entity:
            return set()
        return self.term2entity[term]

    def __tag_entity_recursive(self, term: str, expand_search_by_prefix=True) -> Set[Entity]:
        # Lower, strip and remove all punctuation
        t_low = term.lower().translate(self.__translator).strip()
        entities = set()

        # fix working with empty strings here
        if not t_low.strip():
            return entities

        if expand_search_by_prefix:
            if not self.autocompletion:
                from narraint.frontend.entity import autocompletion
                self.autocompletion = autocompletion.AutocompletionUtil()
            expanded_terms = self.autocompletion.find_entities_starting_with(t_low, retrieve_k=1000)
            logging.debug(f'Expanding term "{t_low}" with: {expanded_terms}')
            for term in expanded_terms:
                entities.update(self.__tag_entity_recursive(term, expand_search_by_prefix=False))

        # check direct string
        entities.update(self.__find_entities(t_low))
        # also add plural if possible
        if t_low[-1] != 's':
            entities.update(self.__find_entities(f'{t_low}s'))
        # check singular form
        if t_low[-1] == 's':
            entities.update(self.__find_entities(t_low[:-1]))
        # some drugs might be searched without the ending "e"
        if not expand_search_by_prefix and len(entities) == 0 and t_low[-1] != 'e':
            entities.update(self.__find_entities(f'{t_low}e'))
        return entities

    def tag_entity(self, term: str, expand_search_by_prefix=True) -> Set[Entity]:
        """
        Tags an entity by given a string
        :param term: the entity term
        :param expand_search_by_prefix: If true, all known terms that have the given term as a prefix are used to search
        :return: a list of entities (entity_id, entity_type)
        """
        entities = self.__tag_entity_recursive(term, expand_search_by_prefix=expand_search_by_prefix)
        if len(entities) == 0:
            raise KeyError('Does not know an entity for term: {}'.format(term))
        return entities


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    EntityTagger.LOAD_INDEX = False
    entity_tagger = EntityTagger()
    entity_tagger.store_index()


if __name__ == "__main__":
    main()
