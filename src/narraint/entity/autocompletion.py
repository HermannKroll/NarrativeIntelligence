import itertools
import logging
import os
import pickle
from datetime import datetime
from typing import Set

import marisa_trie

from kgextractiontoolbox.progress import print_progress_with_eta
from narraint.config import AUTOCOMPLETION_TMP_INDEX, AUTOCOMPLETION_PARTIAL_TERM_THRESHOLD
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.entitylinking.enttypes import DRUG, ALL


class AutocompletionUtil:
    __instance = None

    VERSION = 5
    LOAD_INDEX = True

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.variable_types = set()
            cls.__instance.variable_types.update(ALL)
            cls.__instance.variable_types.add("Target")
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
        return marisa_trie.Trie([s.lower() for s in known_terms])

    @staticmethod
    def remove_redundant_terms(terms: Set[str]) -> Set[str]:
        cleaned_terms = set()
        for term in terms:
            # Rule 1:
            # If word without tailing s is although contained, we don't need the longer term
            # do not force the rules if words are too short
            # e.g. complications is removed if complication is present
            if len(term) >= 5 and term[-1] == 's' and term[:-1] in terms:
                continue

            # add term if no rule fired
            cleaned_terms.add(term)

        return cleaned_terms

    def build_autocompletion_index(self, index_path=AUTOCOMPLETION_TMP_INDEX):
        self.known_terms.clear()
        self.trie = None
        self.compute_known_entities_in_db()

        # allow entity types as strings
        self.known_terms.add("target")
        self.known_terms.update([t for t in self.variable_types])
        self.known_terms.update([t for t in self.other_terms])

        logging.info('Cleaning known terms...')
        self.known_terms = AutocompletionUtil.remove_redundant_terms(self.known_terms)
        self.known_drug_terms = AutocompletionUtil.remove_redundant_terms(self.known_drug_terms)

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
    def remove_term_ending_comma(entity_str: str):
        # some terms like "Diabetes Mellitus, Adult" contain terms that end with a ',' - remove those ','
        # but do not remove commas in words like cyp3,a4
        return entity_str.replace(', ', ' ')

    @staticmethod
    def capitalize_entity(entity_str: str) -> str:
        return ' '.join([s.capitalize() for s in entity_str.strip().split(' ')])

    @staticmethod
    def iterate_entity_name_orders(entity_str: str, recursive_call=False):
        results = list()
        # do not alternate terms with 'for', 'of', or 'off'
        # since this would break the logical order
        if "For" in entity_str or "Of" in entity_str or "Off" in entity_str:
            return results

        partial_entity_terms = None
        and_index = entity_str.find(" And ")
        or_index = entity_str.find(" Or ")
        if and_index > 0 or or_index > 0:
            # we have found a conjunction (and, or)
            # example: "t1 and t2 or t3" should create
            # "t1 and t2 or t3"
            # "t2 and t1 or t3"
            # "t1 and t3 or t2"
            # "t3 and t1 or t2"
            # "t2 and t3 or t1"
            # "t3 and t2 or t1"

            if 0 <= and_index < or_index or or_index == -1:
                # "and" occurred first
                left_str, right_str = entity_str.split(" And ",  1)
                left_terms = AutocompletionUtil.iterate_entity_name_orders(left_str.strip(), recursive_call=True)
                right_terms = AutocompletionUtil.iterate_entity_name_orders(right_str.strip(), recursive_call=True)
                conjunction = " And "
            else:  # 0 <= or_index < and_index or and_index == -1
                # "or" occurred first
                left_str, right_str = entity_str.split(" Or ", 1)
                left_terms = AutocompletionUtil.iterate_entity_name_orders(left_str.strip(), recursive_call=True)
                right_terms = AutocompletionUtil.iterate_entity_name_orders(right_str.strip(), recursive_call=True)
                conjunction = " Or "

            # recursive call invalid (len(term.split()) > AUTOCOMPLETION_PARTIAL_TERM_THRESHOLD)
            if len(left_terms) == 0:
                left_terms = [left_str]
            if len(right_terms) == 0:
                right_terms = [right_str]

            partial_entity_terms = (left_terms, conjunction, right_terms)

        if not partial_entity_terms:
            entity_terms = entity_str.split(' ')
            # skip to long terms as they would lead to
            # 1) too many different permutations and
            # 2) increase the index size by factors
            # Stopping at 4 (2025, 02) 34MB (in-memory & on disk)
            if len(entity_terms) > AUTOCOMPLETION_PARTIAL_TERM_THRESHOLD:
                return results

            for alternate_order in itertools.permutations(entity_terms):
                results.append(' '.join(alternate_order))
        elif recursive_call:
            return partial_entity_terms
        else:
            term_component_permutations = list()
            left_terms, conjunction, right_terms = partial_entity_terms
            term_component_permutations.append(left_terms)
            conjunction_pattern = "{}" + conjunction + "{}"

            while isinstance(right_terms, tuple):
                assert len(right_terms) == 3
                left_terms, conjunction, right_terms = right_terms
                term_component_permutations.append(left_terms)
                conjunction_pattern += conjunction + "{}"

            term_component_permutations.append(right_terms)

            for term_component_choice in itertools.product(*term_component_permutations):
                # term_component_permutations = (['ab', 'ba'], ['cd', 'dc'], ['ef', 'fe'])
                # term_component_choice = ('ab', 'cd', 'ef') --> insert into pattern
                for choice_permutation in itertools.permutations(term_component_choice):
                    results.append(conjunction_pattern.format(*choice_permutation))

        return results

    def add_entity_to_dict(self, entity_type, entity_str):
        str_formated = AutocompletionUtil.capitalize_entity(entity_str)
        str_formated = AutocompletionUtil.remove_term_ending_comma(str_formated)
        self.known_terms.add(str_formated)
        for alternate_order in AutocompletionUtil.iterate_entity_name_orders(str_formated):
            self.known_terms.add(alternate_order)

        # special handling of drug terms
        # required for name suggestions of drug overviews
        if entity_type == DRUG:
            self.known_drug_terms.add(str_formated)
            for alternate_order in AutocompletionUtil.iterate_entity_name_orders(str_formated):
                self.known_drug_terms.add(alternate_order)

    def compute_known_entities_in_db(self):
        # Write dosage form terms + synonyms
        logging.info('Adding entity tagger entries...')
        tagger = EntityTagger()
        start_time = datetime.now()
        known_terms_to_types = tagger.known_terms()
        task_size = len(known_terms_to_types)
        for idx, term in enumerate(known_terms_to_types):
            try:
                for entity_type in known_terms_to_types[term]:
                    self.add_entity_to_dict(entity_type, term)
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
