import itertools
import logging
import pickle
import sys
from collections import defaultdict

from pytrie import Trie, SortedTrie, SortedStringTrie

from narraint.config import AUTOCOMPLETION_TMP_INDEX
from narraint.entity.entityresolver import EntityResolver
from narraint.entity.entitytagger import DosageFormTaggerVocabulary
from narraint.entity.enttypes import CHEMICAL, DISEASE, DOSAGE_FORM, GENE, SPECIES, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT, \
    PLANT_FAMILY
from narraint.entity.meshontology import MeSHOntology
from narraint.queryengine.engine import QueryEngine

from typing import Tuple


PREDICATE_TYPING = {'treats': ([CHEMICAL, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT], [DISEASE, SPECIES]),
                    'administered': ([DOSAGE_FORM], [SPECIES, DISEASE, CHEMICAL, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT]),
                    'induces': ([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE], [CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE]),
                    'decreases': ([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE], [CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE]),
                    'interacts': ([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, GENE], [CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, GENE]),
                    'metabolises': ([GENE], [CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL]),
                    'inhibits': ([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL], [GENE])
                    }


class AutocompletionUtil:

    def __init__(self, logger=logging):
        self.variable_types = {CHEMICAL, DISEASE, DOSAGE_FORM, GENE, SPECIES, PLANT_FAMILY, EXCIPIENT, DRUG, DRUGBANK_CHEMICAL}
        self.logger = logger
        self.known_entities = defaultdict(set)
        self.entity_type_roots = {}
        self.trie = SortedTrie()

    def build_autocompletion_index(self):
        self.compute_known_entities_in_db()
        self.logger.info(f'Storing index structure to: {AUTOCOMPLETION_TMP_INDEX}')
        with open(AUTOCOMPLETION_TMP_INDEX, 'wb') as f:
            pickle.dump(self.known_entities, f)

    def load_autocompletion_index(self):
        self.logger.info('Loading autocompletion index...')
        with open(AUTOCOMPLETION_TMP_INDEX, 'rb') as f:
            self.known_entities = pickle.load(f)

        self.logger.info('Building Trie structure...')
        self.trie = SortedStringTrie()
        for e_type, terms in self.known_entities.items():
            for t in terms:
                self.trie[t.lower()] = t
        self.known_entities = None
        self.logger.info('Finished')


    def add_entity_to_dict(self, entity_type, entity_str):
        str_formated = (' '.join([s.capitalize() for s in entity_str.strip().split(' ')]))
        self.known_entities[entity_type].add(str_formated)

    def compute_known_entities_in_db(self):
        resolver = EntityResolver()
        self.logger.info('Query entities in Predication...')
        entities = QueryEngine.query_entities()
        mesh_ontology = MeSHOntology.instance()
        ignored = set()

        # Write dosage form terms + synonyms
        for df_id, terms in DosageFormTaggerVocabulary.get_dosage_form_vocabulary_terms().items():
            for t in terms:
                if not t.endswith('s'):
                    t = '{}s'.format(t)
                t = t.replace('-', ' ')
                if df_id.startswith('D'):
                    df_id = 'MESH:{}'.format(df_id)
                self.add_entity_to_dict(DOSAGE_FORM, t)

        # check all known mesh entities
        known_mesh_prefixes = set()
        for e_id, e_str, e_type in entities:
            if e_type in [CHEMICAL, DISEASE, DOSAGE_FORM] and not e_id.startswith('MESH:') and not e_id.startswith(
                    'DB'):
                # Split MeSH Tree No by .
                split_tree_number = e_id.split('.')
                # add all known concepts and superconcepts to our index
                # D02
                # D02.255
                # D02.255.234
                for x in range(0, len(split_tree_number)):
                    known_prefix = '.'.join(split_tree_number[0:x + 1])
                    known_mesh_prefixes.add(known_prefix)

        # write the mesh tree C and D
        mesh_to_export = itertools.chain(mesh_ontology.find_descriptors_start_with_tree_no("D"),
                                         mesh_ontology.find_descriptors_start_with_tree_no("C"),
                                         mesh_ontology.find_descriptors_start_with_tree_no("J01"),
                                         mesh_ontology.find_descriptors_start_with_tree_no("E02"))
        for d_id, d_heading in mesh_to_export:
            export_desc = False
            entity_type = None
            for tn in mesh_ontology.get_tree_numbers_for_descriptor(d_id):
                if tn in known_mesh_prefixes:
                    if tn.startswith('D'):
                        entity_type = CHEMICAL
                    elif tn.startswith('C'):
                        entity_type = DISEASE
                    else:
                        entity_type = DOSAGE_FORM
                    export_desc = True
                    break
            if export_desc:
                self.add_entity_to_dict(entity_type, d_heading)

        written_entity_ids = set()
        for e_id, e_str, e_type in entities:
            #self.add_entity_to_dict(e_type, e_str)
            try:
                # Skip duplicated entries
                if (e_id, e_type) in written_entity_ids:
                    continue
                written_entity_ids.add((e_id, e_type))

                heading = resolver.get_name_for_var_ent_id(e_id, e_type, resolve_gene_by_id=False)
                if e_type in [GENE, SPECIES] and '//' in heading:
                    for n in heading.split('//'):
                        self.add_entity_to_dict(e_type, n)
                else:
                    self.add_entity_to_dict(e_type, heading)

            except KeyError:
                ignored.add((e_id, e_type))

        logging.info('The following entities are not in index: {}'.format(ignored))

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

    def find_entities_starting_with(self, start_str: str, retrieve_k=10):
        hits = self.trie.keys(start_str)[:retrieve_k]
        formated_hits = []
        for h in hits:
            formated_hits.append((' '.join([s.capitalize() for s in h.strip().split(' ')])))
        return formated_hits

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
            completions.extend(self.find_entities_starting_with(relevant_term))

        # shortest completions first
        sorted_by_length = sorted(completions, key=lambda x: len(x))[0:10]
        # sort alphabetically
        return sorted(sorted_by_length)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    ac = AutocompletionUtil()
   # ac.build_autocompletion_index()
    ac.load_autocompletion_index()

    print('Diabetes: ', ac.trie.keys('Diabetes'))
    print('Simva: ', ac.trie.keys('Simva'))
    print('Metfor: ', ac.trie.keys('Metfor'))

if __name__ == "__main__":
    main()