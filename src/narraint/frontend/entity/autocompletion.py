import logging
import os
import pickle
from datetime import datetime

import datrie

from narraint.config import AUTOCOMPLETION_TMP_INDEX
from narraint.frontend.entity.entitytagger import DosageFormTaggerVocabulary, EntityTagger
from narrant.preprocessing.enttypes import CHEMICAL, DISEASE, DOSAGE_FORM, SPECIES, DRUG, CHEMBL_CHEMICAL, EXCIPIENT, \
    PLANT_FAMILY, ENT_TYPES_SUPPORTED_BY_TAGGERS, METHOD, LAB_METHOD
from narrant.progress import print_progress_with_eta


class AutocompletionUtil:
    __instance = None

    @staticmethod
    def instance(load_index=True):
        if AutocompletionUtil.__instance is None:
            AutocompletionUtil(load_index=load_index)
        return AutocompletionUtil.__instance

    def __init__(self, logger=logging, load_index=True):
        if AutocompletionUtil.__instance is not None:
            raise Exception('This class is a singleton - use AutocompletionUtil.instance()')
        else:
            self.variable_types = {CHEMICAL, DISEASE, DOSAGE_FORM, "Target", SPECIES, PLANT_FAMILY, EXCIPIENT, DRUG,
                                   CHEMBL_CHEMICAL, METHOD, LAB_METHOD}
            self.logger = logger
            self.known_terms = set()
            self.trie = None
            if load_index:
                self.load_autocompletion_index()
            AutocompletionUtil.__instance = self

    def build_autocompletion_index(self, index_path=AUTOCOMPLETION_TMP_INDEX):
        self.known_terms.clear()
        self.trie = None
        self.compute_known_entities_in_db()
        self.logger.info(f'Building Trie structure with {len(self.known_terms)} terms...')
        alphabet = {c for t in self.known_terms for c in t}
        self.logger.info(f'{len(alphabet)} different characters are in the alphabet')

        # allow entity types as strings
        self.known_terms.add("target")
        self.known_terms.update([t for t in ENT_TYPES_SUPPORTED_BY_TAGGERS])

        # self.trie = SortedStringTrie(zip(self.known_terms, range(len(self.known_terms))))
        start_time = datetime.now()
        self.trie = datrie.Trie(alphabet)
        for idx, t in enumerate(self.known_terms):
            self.trie[t.lower()] = t
            print_progress_with_eta("computing trie", idx, len(self.known_terms), start_time)
        self.logger.info('Finished')

        self.logger.info(f'Storing index structure to: {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump((self.trie, self.known_terms), f)

    def load_autocompletion_index(self, index_path=AUTOCOMPLETION_TMP_INDEX):
        if os.path.isfile(index_path):
            self.logger.info('Loading autocompletion index...')
            with open(index_path, 'rb') as f:
                self.trie, self.known_terms = pickle.load(f)
        else:
            self.logger.info(f'Autocompletion index does not exists: {index_path}')

    @staticmethod
    def capitalize_entity(entity_str: str) -> str:
        return ' '.join([s.capitalize() for s in entity_str.strip().split(' ')])

    def add_entity_to_dict(self, entity_type, entity_str):
        str_formated = AutocompletionUtil.capitalize_entity(entity_str)
        self.known_terms.add(str_formated)

    def compute_known_entities_in_db(self):
        # Write dosage form terms + synonyms
        for df_id, terms in DosageFormTaggerVocabulary.get_dosage_form_vocabulary_terms().items():
            for t in terms:
                if not t.endswith('s'):
                    t = '{}s'.format(t)
                t = t.replace('-', ' ')
                if df_id.startswith('D'):
                    df_id = 'MESH:{}'.format(df_id)
                self.add_entity_to_dict(DOSAGE_FORM, t)

        logging.info('Adding entity tagger entries...')
        tagger = EntityTagger.instance()
        start_time = datetime.now()
        task_size = len(tagger.term2entity.items())
        for idx, (term, t_entities) in enumerate(tagger.term2entity.items()):
            for e in t_entities:
                self.add_entity_to_dict(e.entity_type, term)
            print_progress_with_eta('adding entity tagger terms...', idx, task_size, start_time)

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

    def autocomplete(self, start_str: str):
        return self.trie.keys(start_str.lower())

    def find_entities_starting_with(self, start_str: str, retrieve_k=10):
        hits = self.autocomplete(start_str)
        hits.sort()
        formatted_hits = []
        for h in hits[0:retrieve_k]:
            formatted_hits.append(AutocompletionUtil.capitalize_entity(h))
        return formatted_hits

    def compute_autocompletion_list(self, search_str: str):
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
        # search for entity
        else:
            try:
                completions.extend(self.find_entities_starting_with(relevant_term))
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

    ac = AutocompletionUtil.instance()
    ac.build_autocompletion_index()


if __name__ == "__main__":
    main()
