import ast
import itertools
import json
import logging
import os.path
import pickle
import re
import string
from copy import copy
from typing import Set, List

import nltk
from sqlalchemy import delete

from kgextractiontoolbox.backend.retrieve import iterate_over_all_documents_in_collection
from kgextractiontoolbox.cleaning.relation_type_constraints import RelationTypeConstraintStore
from kgextractiontoolbox.cleaning.relation_vocabulary import RelationVocabulary
from kgextractiontoolbox.progress import Progress
from narraint.analysis.querytranslation.data_graph import DataGraph
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, Document, JCDLInvertedTermIndex, \
    JCDLInvertedEntityIndex, JCDLInvertedStatementIndex
from narraint.config import PHARM_RELATION_VOCABULARY, PHARM_RELATION_CONSTRAINTS
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.query import GraphQuery
from narraint.queryengine.query_hints import SYMMETRIC_PREDICATES, PREDICATE_EXPANSION
from narrant.entity.meshontology import MeSHOntology

QUERY_1 = "Metformin Diabetes"
QUERY_2 = "Metformin treats Diabetes"
QUERY_3 = "Metformin mtor Injection DiaBeTes"
QUERY_4 = 'Mass Spectrometry method Simvastatin'
QUERY_5 = "Simvastatin Rhabdomyolysis Target"
QUERIES = [QUERY_1, QUERY_2, QUERY_3, QUERY_4, QUERY_5]

TERM_FREQUENCY_UPPER_BOUND = 0.99
TERM_FREQUENCY_LOWER_BOUND = 0
TERM_MIN_LENGTH = 3

DATA_GRAPH_CACHE = "/home/kroll/jcdl2023_datagraph_improved.pkl"


# nltk.download('stopwords')


class SchemaGraph:

    def __init__(self):
        self.__load_schema_graph()

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
        logging.info('Finished')

    def find_possible_relations_for_entity_types(self, subject_type, object_type):
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


class QueryTranslationToGraph:

    def __init__(self, data_graph: DataGraph, schema_graph: SchemaGraph):
        print('Init query translation...')
        self.tagger = EntityTaggerJCDL.instance()
        self.schema_graph: SchemaGraph = schema_graph
        self.data_graph: DataGraph = data_graph
        print('Query translation ready')

    def __greedy_find_dict_entries_in_keywords(self, keywords, lookup_dict):
        term2dictentries = {}
        for i in range(self.schema_graph.max_spaces_in_entity_types, 0, -1):
            for j in range(len(keywords)):
                combined_word = ' '.join([k for k in keywords[j:j + i]])
                if combined_word in lookup_dict:
                    if combined_word in term2dictentries:
                        raise ValueError(
                            f'Current string {combined_word} was already mapped before (duplicated keyword?)')
                    term2dictentries[combined_word] = lookup_dict[combined_word]
        return term2dictentries

    def __greedy_find_predicates_in_keywords(self, keywords):
        term2predicates = self.__greedy_find_dict_entries_in_keywords(keywords, self.schema_graph.relation_dict)
        print('Term2predicate mapping: ')
        for k, v in term2predicates.items():
            print(f'    {k} -> {v}')
        return term2predicates

    def __greedy_find_entity_types_variables_in_keywords(self, keywords):
        term2variables = self.__greedy_find_dict_entries_in_keywords(keywords, self.schema_graph.entity_types)
        print('Term2EntityTypeVariable mapping: ')
        for k, v in term2variables.items():
            print(f'    {k} -> {v}')
        return term2variables

    def __greedy_find_entities_in_keywords(self, keywords):
        logging.debug('--' * 60)
        logging.debug('--' * 60)
        keywords_remaining = copy(keywords)
        keywords_not_mapped = list()
        term2entities = {}
        while keywords_remaining:
            found = False
            i = 0
            for i in range(len(keywords_remaining), 0, -1):
                current_part = ' '.join([k for k in keywords_remaining[:i]])
                # logging.debug(f'Checking query part: {current_part}')
                try:
                    entities_in_part = self.tagger.tag_entity(current_part, expand_search_by_prefix=False)
                    if current_part in term2entities:
                        raise ValueError(
                            f'Current string {current_part} was already mapped before (duplicated keyword?)')
                    term2entities[current_part] = entities_in_part
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
        print('Term2Entity mapping: ')
        for k, v in term2entities.items():
            print(f'    {k} -> {v}')

        logging.debug('--' * 60)
        logging.debug('--' * 60)
        return term2entities

    def translate_keyword_query(self, keyword_query) -> GraphQuery:
        keyword_query = keyword_query.lower().strip()
        keywords = keyword_query.split(' ')
        term2predicates = self.__greedy_find_predicates_in_keywords(keywords)
        term2variables = self.__greedy_find_entity_types_variables_in_keywords(keywords)
        term2entities = self.__greedy_find_entities_in_keywords(keywords)  #

        print(term2entities)
        possible_relations = list()

        print('--' * 60)
        print('Term support')
        print('--' * 60)
        for term in keywords:
            document_ids = self.data_graph.get_document_ids_for_term(term=term)
            print(f'{len(document_ids)} support: {term}')

        print('--' * 60)
        print('Entity support')
        print('--' * 60)
        for term, entities in term2entities.items():
            for entity in entities:
                document_ids = self.data_graph.get_document_ids_for_entity(entity_id=entity)
                print(f'{len(document_ids)} support: {term} ---> {entity}')

        print('--' * 60)
        print('Statement support')
        print('--' * 60)
        for term1 in term2entities:
            for term2 in term2entities:
                if term1 == term2:
                    continue
                subject_ids = term2entities[term1]
                object_ids = term2entities[term2]

                for subject_id in subject_ids:
                    for object_id in object_ids:
                        for relation in self.schema_graph.relation_dict:
                            document_ids = self.data_graph.get_document_ids_for_statement(subject_id=subject_id,
                                                                                          relation=relation,
                                                                                          object_id=object_id)
                            if len(document_ids) > 0:
                                print(f'{len(document_ids)} support: {subject_id} x {relation} x {object_id}')
                                possible_relations.append((len(document_ids), subject_id, relation, object_id))
        return GraphQuery()


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    trans = QueryTranslationToGraph(data_graph=DataGraph(), schema_graph=SchemaGraph())
    for q in QUERIES:
        logging.info('==' * 60)
        logging.info(f'Translating query: "{q}"')
        graph_q = trans.translate_keyword_query(q)
        logging.info('==' * 60)


if __name__ == "__main__":
    main()
