import logging
import os
import pickle
from datetime import datetime

import datrie

from kgextractiontoolbox.progress import print_progress_with_eta
from narraint.config import AUTOCOMPLETION_TMP_INDEX
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entitylinking.enttypes import CHEMICAL, DISEASE, DOSAGE_FORM, SPECIES, DRUG, CHEMBL_CHEMICAL, EXCIPIENT, \
    PLANT_FAMILY_GENUS, ENT_TYPES_SUPPORTED_BY_TAGGERS, METHOD, LAB_METHOD, VACCINE, ORGANISM, TARGET, TISSUE, \
    HEALTH_STATUS


class AutocompletionUtil:
    __instance = None

    VERSION = 3
    LOAD_INDEX = True

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.variable_types = {CHEMICAL, DISEASE, DOSAGE_FORM, "Target",
                                             SPECIES, PLANT_FAMILY_GENUS, EXCIPIENT, DRUG, CHEMBL_CHEMICAL, METHOD,
                                             LAB_METHOD, VACCINE, TARGET, ORGANISM, TISSUE, HEALTH_STATUS}
            cls.__instance.variable_types.update(ENT_TYPES_SUPPORTED_BY_TAGGERS)
            cls.__instance.other_terms = list(["PlantGenus", "PlantGenera"])
            cls.__instance.variable_types = sorted(list(cls.__instance.variable_types))

            cls.__instance.logger = logging
            cls.__instance.known_terms = set()
            cls.__instance.known_drug_terms = set()
            cls.__instance.trie = None
            cls.__instance.drug_trie = None
            cls.__instance.version = None
            if AutocompletionUtil.LOAD_INDEX:
                try:
                    cls.__instance.load_autocompletion_index()
                except ValueError:
                    logging.info('Autocompletion index is outdated. Creating a new one...')
                    cls.__instance.build_autocompletion_index()
        return cls.__instance

    def __build_trie_structure(self, known_terms):
        self.logger.info(f'Building Trie structure with {len(known_terms)} terms...')
        alphabet = {c for t in known_terms for c in t}
        self.logger.info(f'{len(alphabet)} different characters are in the alphabet')
        start_time = datetime.now()
        trie = datrie.Trie(alphabet)
        for idx, t in enumerate(known_terms):
            trie[t.lower()] = t
            print_progress_with_eta("computing trie", idx, len(known_terms), start_time)
        self.logger.info('Finished')
        return trie

    def build_autocompletion_index(self, index_path=AUTOCOMPLETION_TMP_INDEX):
        self.known_terms.clear()
        self.trie = None
        self.compute_known_entities_in_db()

        # allow entity types as strings
        self.known_terms.add("target")
        self.known_terms.update([t for t in self.variable_types])
        self.known_terms.update([t for t in self.other_terms])

        self.trie = self.__build_trie_structure(known_terms=self.known_terms)
        self.drug_trie = self.__build_trie_structure(known_terms=self.known_drug_terms)

        self.logger.info(f'Storing index structure to: {index_path}')
        self.version = AutocompletionUtil.VERSION
        with open(index_path, 'wb') as f:
            pickle.dump((self.version, self.trie, self.drug_trie), f)

    def load_autocompletion_index(self, index_path=AUTOCOMPLETION_TMP_INDEX):
        if os.path.isfile(index_path):
            self.logger.info('Loading autocompletion index...')
            with open(index_path, 'rb') as f:
                self.version, self.trie, self.drug_trie = pickle.load(f)

                if self.version != AutocompletionUtil.VERSION:
                    raise ValueError('Autocompletion index is outdated.')
        else:
            self.logger.info(f'Autocompletion index does not exists: {index_path}')

    @staticmethod
    def capitalize_entity(entity_str: str) -> str:
        return ' '.join([s.capitalize() for s in entity_str.strip().split(' ')])

    def add_entity_to_dict(self, entity_type, entity_str):
        str_formated = AutocompletionUtil.capitalize_entity(entity_str)
        self.known_terms.add(str_formated)
        if entity_type == DRUG:
            self.known_drug_terms.add(str_formated)

    def compute_known_entities_in_db(self):
        # Write dosage form terms + synonyms
        logging.info('Adding entity tagger entries...')
        tagger = EntityTagger()
        start_time = datetime.now()
        task_size = len(tagger.term2entity.items())
        for idx, term in enumerate(tagger.known_terms):
            try:
                for e in tagger.tag_entity(term, expand_search_by_prefix=False):
                    self.add_entity_to_dict(e.entity_type, term)
                print_progress_with_eta('adding entity tagger terms...', idx, task_size, start_time)
            except KeyError:
                pass

        logging.info('Index built')

    @staticmethod
    def prepare_search_str(search_str: str) -> str:
        # get the relevant search str
        search_str_lower = search_str.lower().strip()
        # replace multiple spaces by a single one
        search_str_lower = ' '.join(search_str_lower.split())
        search_str_lower = search_str_lower.replace(';', '.')

        # ignore old facts
        if '.' in search_str_lower:
            # just take the latest fact in the current search term
            search_str_lower = search_str_lower.split('.')[-1]

        return search_str_lower

    def autocomplete(self, start_str: str, entity_type: str = None):
        start_str = start_str.lower()
        if entity_type == DRUG:
            return self.drug_trie.keys(start_str)
        else:
            return self.trie.keys(start_str)

    def find_entities_starting_with(self, start_str: str, retrieve_k=10, entity_type: str = None):
        hits = self.autocomplete(start_str, entity_type=entity_type)
        hits.sort()
        formatted_hits = []
        for h in hits[0:retrieve_k]:
            formatted_hits.append(AutocompletionUtil.capitalize_entity(h))
        return formatted_hits

    def compute_autocompletion_list(self, search_str: str, entity_type: str = None):
        if len(search_str) < 2:
            return []
        relevant_term = AutocompletionUtil.prepare_search_str(search_str)
        completions = []
        # is a variable?
        if relevant_term.startswith('?'):
            # ignore leading question mark
            var_name = relevant_term[1:].split('(')[0]
            hits = [f'?{var_name.capitalize()}({var_type})' for var_type in self.variable_types]
            for h in hits:
                if h.lower().startswith(relevant_term):
                    completions.append(h)
            # Var Names are already sorted (sorting by shortest completion does not apply here)
            return completions
        # search for entity
        else:
            try:
                completions.extend(self.find_entities_starting_with(relevant_term, entity_type=entity_type))
            except AttributeError:
                pass

        # shortest completions first
        sorted_by_length = sorted(completions, key=lambda x: len(x))[0:10]
        # sort alphabetically
        return sorted(sorted_by_length)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    AutocompletionUtil.LOAD_INDEX = False
    ac = AutocompletionUtil()
    ac.build_autocompletion_index()


if __name__ == "__main__":
    main()
