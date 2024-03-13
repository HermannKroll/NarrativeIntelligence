import logging
import pickle
import string
from collections import defaultdict

from narraint.config import ENTITY_EXPLAINER_INDEX
from narraint.frontend.entity.entityindexbase import EntityIndexBase
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entity.entityresolver import EntityResolver


class EntityExplainer(EntityIndexBase):
    __instance = None

    VERSION = 3

    def __new__(cls, load_index=True):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            logging.info('Initialize EntityTagger...')
            cls.__instance.expand_by_subclasses = False
            cls.__instance.entity2terms = defaultdict(set)
            cls.__instance.version = None
            trans_map = {p: '' for p in string.punctuation}
            cls.__instance.__translator = str.maketrans(trans_map)
            if load_index:
                try:
                    cls.__instance._load_index()
                except ValueError:
                    # The index has been outdated or is old - create a new one
                    logging.info('Index is outdated. Creating a new one...')
                    cls.__instance.store_index()
        return cls.__instance

    def _load_index(self, index_path=ENTITY_EXPLAINER_INDEX):
        logging.info(f'Loading entity explainer index from {index_path}')
        with open(index_path, 'rb') as f:
            self.version, self.entity2terms = pickle.load(f)

            if self.version != EntityExplainer.VERSION:
                raise ValueError('EntityExplainer index is outdated.')

        logging.info(f'Index load ({len(self.entity2terms)} different terms)')

    def store_index(self, index_path=ENTITY_EXPLAINER_INDEX):
        self.version = EntityExplainer.VERSION
        logging.info('Computing entity explainer index...')
        self._create_index()
        logging.info(f'Storing index to {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump((self.version, self.entity2terms), f)
        logging.info('Index stored')

    def _add_term(self, term, entity_id: str, entity_type: str, entity_class: str = None):
        self.entity2terms[entity_id].add(term.strip())

    def get_prefixes(self, name):
        words = list([n for n in name.translate(self.__translator).lower().split(' ')])
        for i in range(len(words), 0, -1):
            yield ' '.join([k for k in words[:i]])

    def filter_names_for_prefix_duplicates(self, names):
        selected_headings = []
        known_prefixes = set()
        for h in names:
            already_selected = False

            h_prefixes = list(self.get_prefixes(h))
            for prefix in h_prefixes:
                if prefix in known_prefixes:
                    already_selected = True
                    break

            # Skip word. A prefix word has already been selected
            if already_selected:
                continue

            known_prefixes.add(h.translate(self.__translator).lower())
            selected_headings.append(h)

        return selected_headings

    def explain_entities(self, entities, truncate_at_k=25):
        resolver = EntityResolver()
        headings = set()
        # Add all headings and known terms for the possible entity ids
        for entity in entities:
            heading = resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type, resolve_gene_by_id=False)
            headings.add(heading)
            if entity.entity_id in self.entity2terms:
                for term in self.entity2terms[entity.entity_id]:
                    headings.add(term)

        # Convert it to a list and sort
        headings = list([h for h in headings if len(h) > 1])
        headings.sort()

        # Remove headings that have the same prefix
        headings = self.filter_names_for_prefix_duplicates(headings)

        heading_len = len(headings)
        if heading_len > truncate_at_k:
            headings = headings[:truncate_at_k]
            headings.append(f"and {heading_len - truncate_at_k} more")

        return headings

    def explain_entity_str(self, entity_str, truncate_at_k=25):
        tagger = EntityTagger()
        entities = tagger.tag_entity(entity_str)
        return self.explain_entities(entities, truncate_at_k=truncate_at_k)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    entity_explainer = EntityExplainer(load_index=False)
    entity_explainer.store_index()


if __name__ == "__main__":
    main()
