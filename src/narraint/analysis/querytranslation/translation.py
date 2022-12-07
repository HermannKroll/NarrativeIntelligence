import itertools
import logging
from copy import copy
from typing import Set

from kgextractiontoolbox.cleaning.relation_type_constraints import RelationTypeConstraintStore
from kgextractiontoolbox.cleaning.relation_vocabulary import RelationVocabulary
from narraint.config import PHARM_RELATION_VOCABULARY, PHARM_RELATION_CONSTRAINTS
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.query import GraphQuery
from narrant.entity.entity import Entity

QUERY_1 = "Metformin Diabetes"
QUERY_2 = "Metformin treats Diabetes"
QUERY_3 = "Metformin mtor Injection DiaBeTes"
QUERY_4 = 'Mass Spectrometry method Simvastatin'
QUERY_5 = "Simvastatin Rhabdomyolysis Target"
QUERIES = [QUERY_1, QUERY_2, QUERY_3, QUERY_4, QUERY_5]


class QueryTranslationToGraph:

    def __init__(self):
        logging.info('Init query translation...')
        self.tagger = EntityTagger.instance()
        self.__load_schema_graph()
        self.data_graph = None
        logging.info('Query translation ready')

    def __load_schema_graph(self):
        translation = QueryTranslation()
        self.entity_types = translation.variable_type_mappings
        self.max_spaces_in_entity_types = max([len(t.split(' ')) - 1 for t in self.entity_types])
        logging.info(f'Longest entity type has {self.max_spaces_in_entity_types} spaces')
        self.relation_vocab = RelationVocabulary()
        self.relation_vocab.load_from_json(PHARM_RELATION_VOCABULARY)
        logging.info(f'Relation vocab with {len(self.relation_vocab.relation_dict)} relations load')
        self.relation_dict = {k: k for k in self.relation_vocab.relation_dict.keys()}

        logging.info('Load relation constraint file...')
        self.relation_type_constraints = RelationTypeConstraintStore()
        self.relation_type_constraints.load_from_json(PHARM_RELATION_CONSTRAINTS)
        self.relations = self.relation_dict.keys()

    def __find_possible_relations_for_entity_types(self, subject_type, object_type):
        allowed_relations = set()
        for r in self.relations:
            # If the relation is constrained, check the constraints
            if r in self.relation_type_constraints.constraints:
                s_const = subject_type in self.relation_type_constraints.get_subject_constraints(r)
                o_const = object_type in self.relation_type_constraints.get_object_constraints(r)
                if s_const and o_const:
                    allowed_relations.add(r)
            else:
                # It is not constrained - so it does work
                allowed_relations.add(r)
        return allowed_relations

    def __greedy_find_dict_entries_in_keywords(self, keywords, lookup_dict):
        term2dictentries = list()
        for i in range(self.max_spaces_in_entity_types, 0, -1):
            for j in range(len(keywords)):
                combined_word = ' '.join([k for k in keywords[j:j + i]])
                if combined_word in lookup_dict:
                    term2dictentries.append((combined_word, lookup_dict[combined_word]))
        return term2dictentries

    def __greedy_find_predicates_in_keywords(self, keywords):
        term2predicates = self.__greedy_find_dict_entries_in_keywords(keywords, self.relation_dict)
        logging.info('Term2predicate mapping: ')
        for k, v in term2predicates:
            logging.info(f'    {k} -> {v}')
        return term2predicates

    def __greedy_find_entity_types_variables_in_keywords(self, keywords):
        term2variables = self.__greedy_find_dict_entries_in_keywords(keywords, self.entity_types)
        logging.info('Term2EntityTypeVariable mapping: ')
        for k, v in term2variables:
            logging.info(f'    {k} -> {v}')
        return term2variables

    def __greedy_find_entities_in_keywords(self, keywords):
        logging.debug('--' * 60)
        logging.debug('--' * 60)
        keywords_remaining = copy(keywords)
        keywords_not_mapped = list()
        term2entities = list()
        while keywords_remaining:
            found = False
            i = 0
            for i in range(len(keywords_remaining), 0, -1):
                current_part = ' '.join([k for k in keywords_remaining[:i]])
                # logging.debug(f'Checking query part: {current_part}')
                try:
                    entities_in_part = self.tagger.tag_entity(current_part)
                    term2entities.append((current_part, entities_in_part))
                    # logging.debug(f'Found: {entities_in_part}')
                    found = True
                    break
                except KeyError:
                    pass
            # Have we found an entity?
            if found:
                # Only consider the remaining rest for the next step
                keywords_remaining = keywords_remaining[i:]
            else:
                # logging.debug(f'Not found entity in part {keywords_remaining} - Ignoring {keywords_remaining[0]}')
                # then ignore the current word
                keywords_not_mapped.append(keywords_remaining[0])
                if len(keywords_remaining) > 1:
                    keywords_remaining = keywords_remaining[1:]
                else:
                    keywords_remaining = None
        terms_mapped = ' '.join([t[0] for t in term2entities])
        logging.debug(f'Found entities in part: {terms_mapped}')
        logging.debug(f'Cannot find entities in part: {keywords_not_mapped}')
        logging.info('Term2Entity mapping: ')
        for k, v in term2entities:
            logging.info(f'    {k} -> {v}')

        logging.debug('--' * 60)
        logging.debug('--' * 60)
        return term2entities

    def __unify_entity_types_in_entity_set(self, entity_set: Set[Entity]):
        e_types = list(set([e.entity_type for e in entity_set]))
        # only a single entity type - easy
        if len(e_types) == 1:
            return e_types
        # What if the same entity id refers to multiple types? Can we resolve it?
        type2id = {}
        for t in e_types:
            type2id[t] = {e.entity_id for e in entity_set if e.entity_type == t}

        # If the length of entity ids is equal between all types, the entities must share the same type
        # In that case both entity types are ok
        if False not in [type2id[e_types[0]] == type2id[e_types[i]] for i in range(1, len(e_types))]:
            # They agree easy
            return e_types

        # They do not agree
        # Return the entity type that has the most found entities
        return list([sorted([(t, len(v)) for t, v in type2id.items()], reverse=True, key=lambda x: x[1])[0][0]])

    def translate_keyword_query(self, keyword_query) -> GraphQuery:
        keyword_query = keyword_query.lower().strip()
        keywords = keyword_query.split(' ')
        term2predicates = self.__greedy_find_predicates_in_keywords(keywords)
        term2variables = self.__greedy_find_entity_types_variables_in_keywords(keywords)
        term2entities = self.__greedy_find_entities_in_keywords(keywords)  #
        term2entity_types = list([(k, self.__unify_entity_types_in_entity_set(v)) for k, v in term2entities])
        logging.info('Unified Term2EntityType mapping: ')
        for k, v in term2entity_types:
            logging.info(f'    {k} -> {v}')

        for idx, (_, et1list) in enumerate(term2entity_types):
            for idx2, (_, et2list) in enumerate(term2entity_types):
                if idx == idx2:
                    continue
                for et1 in et1list:
                    for et2 in et2list:
                        allowed_relations = self.__find_possible_relations_for_entity_types(et1, et2)
                        logging.info(f'Possible relations between "{et1}" and "{et2}" are: "{allowed_relations}"')

        return GraphQuery()


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    trans = QueryTranslationToGraph()
    for q in QUERIES:
        logging.info('==' * 60)
        logging.info(f'Translating query: {q}')
        graph_q = trans.translate_keyword_query(q)
        logging.info('==' * 60)


if __name__ == "__main__":
    main()
