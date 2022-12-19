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

from kgextractiontoolbox.backend.retrieve import iterate_over_all_documents_in_collection
from kgextractiontoolbox.cleaning.relation_type_constraints import RelationTypeConstraintStore
from kgextractiontoolbox.cleaning.relation_vocabulary import RelationVocabulary
from kgextractiontoolbox.progress import Progress
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, Document
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
TERM_FREQUENCY_LOWER_BOUND = 0.001
TERM_MIN_LENGTH = 3

DATA_GRAPH_CACHE = "/home/kroll/jcdl2023_datagraph.pkl"


# nltk.download('stopwords')


def get_document_ids_from_provenance_mappings(provenance_mapping):
    if 'PubMed' in provenance_mapping:
        document_ids = set({int(i) for i in provenance_mapping['PubMed'].keys()})
        return document_ids
    else:
        return {}


def get_key_for_entity(entity_id: str, entity_type: str) -> str:
    return f'{entity_type}_{entity_id}'


class Query:

    def __init__(self):
        self.terms = set()
        self.entities = set()
        self.statements = set()

    def add_term(self, term):
        self.terms.add(term)

    def add_entity(self, entity_id):
        self.entities.add(entity_id)

    def add_statement(self, subject_id, relation, object_id):
        self.statements.add((subject_id, relation, object_id))


class DataGraph:

    def __init__(self):
        self.graph_index = {}
        self.entity_index = {}
        self.term_index = {}
        self.mesh_ontology = None
        self.atc_tree = None

    def resolve_type_and_expand_entity_by_superclasses(self, entity_id: str, entity_type: str) -> Set[str]:
        """
        Expands an entity by all of its superclasses. The type will be integrated as an entity into the results
        :param entity_id: entity id
        :param entity_type: entity type
        :return: a set of entities (no types, only strings)
        """
        if not self.mesh_ontology:
            self.mesh_ontology = MeSHOntology.instance()
            self.atc_tree = ATCTree.instance()

        entities = {entity_id, entity_type}
        # only MeSH has an ontology for now
        if entity_id.startswith('MESH:D'):
            mesh_desc = entity_id.replace('MESH:', '')
            for super_entity, _ in self.mesh_ontology.retrieve_superdescriptors(mesh_desc):
                entities.add(f'MESH:{super_entity}')
            # logging.info(f'Expanded {entity_id} by {entities}')
        # Chembl Drugs
        if entity_id.startswith('CHEMBL'):
            for chembl_class in self.atc_tree.get_classes_for_chembl_id(entity_id):
                entities.add(chembl_class)
        #      logging.info(f'Expanded {entity_id} by {entities}')
        return entities

    def get_document_ids_for_term(self, term: str) -> Set[int]:
        if term not in self.term_index:
            return set()
        return self.term_index[term]

    def get_document_ids_for_entity(self, entity_id) -> Set[int]:
        if entity_id not in self.entity_index:
            return set()
        return self.entity_index[entity_id]

    def get_document_ids_for_statement(self, subject_id, relation, object_id) -> Set[int]:
        if (subject_id, object_id) not in self.graph_index:
            return set()
        if relation not in self.graph_index[(subject_id, object_id)]:
            return set()
        return self.graph_index[(subject_id, object_id)][relation]

    def dump_data_graph(self, file):
        obj_dump = (self.graph_index, self.entity_index, self.term_index)
        pickle.dump(obj_dump, file)

    def load_data_graph(self, file):
        self.graph_index, self.entity_index, self.term_index = pickle.load(file)
        logging.info(f'Terms index with {len(self.term_index)} keys loaded')
        logging.info(f'Graph index with {len(self.graph_index)} keys loaded')
        logging.info(f'Entity index with {len(self.entity_index)} keys loaded')

    def __add_statement_to_index(self, subject_id, relation, object_id, document_ids):
        key = (subject_id, object_id)
        if key not in self.graph_index:
            self.graph_index[key] = {}
        if relation not in self.graph_index[key]:
            self.graph_index[key][relation] = set()
        self.graph_index[key][relation].update(document_ids)

    def __create_graph_index(self, session):
        logging.info('Creating graph index...')
        # iterate over all extracted statements
        total = session.query(PredicationInvertedIndex).count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        q_stmt = session.query(PredicationInvertedIndex).yield_per(1000000)
        for i, r in enumerate(q_stmt):
            progress.print_progress(i)
            subjects = self.resolve_type_and_expand_entity_by_superclasses(entity_id=r.subject_id,
                                                                           entity_type=r.subject_type)
            objects = self.resolve_type_and_expand_entity_by_superclasses(entity_id=r.object_id,
                                                                          entity_type=r.object_type)
            relation = r.relation
            document_ids = get_document_ids_from_provenance_mappings(json.loads(r.provenance_mapping))

            # Cross product between all subjects and all objects
            for subj, obj in itertools.product(subjects, objects):
                self.__add_statement_to_index(subject_id=subj, relation=relation,
                                              object_id=obj, document_ids=document_ids)
                # Swap subject and object im predicate is a symmetric one
                if relation in SYMMETRIC_PREDICATES:
                    self.__add_statement_to_index(subject_id=obj, relation=relation,
                                                  object_id=subj, document_ids=document_ids)
                if relation in PREDICATE_EXPANSION:
                    for expanded_relation in PREDICATE_EXPANSION[relation]:
                        # Expand statement to all of its relations
                        self.__add_statement_to_index(subject_id=subj, relation=expanded_relation,
                                                      object_id=obj, document_ids=document_ids)
                        # Is the relation symmetric again?
                        if expanded_relation in SYMMETRIC_PREDICATES:
                            self.__add_statement_to_index(subject_id=obj, relation=expanded_relation,
                                                          object_id=subj, document_ids=document_ids)

        progress.done()
        logging.info(f'Graph index with {len(self.graph_index)} keys created')

    def __create_entity_index(self, session):
        logging.info('Creating entity index...')
        # iterate over all extracted statements
        total = session.query(TagInvertedIndex).filter(TagInvertedIndex.document_collection == 'PubMed').count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        q_stmt = session.query(TagInvertedIndex).filter(TagInvertedIndex.document_collection == 'PubMed')
        q_stmt = q_stmt.yield_per(1000000)
        for i, r in enumerate(q_stmt):
            progress.print_progress(i)
            document_ids = ast.literal_eval(r.document_ids)
            for entity in self.resolve_type_and_expand_entity_by_superclasses(entity_id=r.entity_id,
                                                                              entity_type=r.entity_type):
                if entity not in self.entity_index:
                    self.entity_index[entity] = set()
                self.entity_index[entity].update(document_ids)

        progress.done()
        logging.info(f'Entity index with {len(self.entity_index)} keys created')

    def __create_term_index(self, session):
        logging.info('Creating term index...')
        # iterate over all extracted statements
        total = session.query(Document).filter(Document.collection == 'PubMed').count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        stopwords = set(nltk.corpus.stopwords.words('english'))
        translator = str.maketrans('', '', string.punctuation)
        term_index_local = {}
        for i, doc in enumerate(iterate_over_all_documents_in_collection(session=session, collection='PubMed')):
            progress.print_progress(i)
            # Make it lower + replace '-' by a space + remove all punctuation
            doc_text = doc.get_text_content().strip().lower()
            doc_text = doc_text.replace('-', ' ')
            doc_text = doc_text.translate(translator)
            for term in doc_text.split(' '):
                if not term.strip() or len(term) <= TERM_MIN_LENGTH or term in stopwords:
                    continue
                if term not in term_index_local:
                    term_index_local[term] = set()
                term_index_local[term].add(doc.id)

        progress.done()
        logging.info('Computing how often each term was found')
        term_frequency = list([(t, len(docs)) for t, docs in term_index_local.items()])
        max_frequency = max(t[1] for t in term_frequency)
        logging.info(f'Most frequent term appears in {max_frequency} documents')
        upper_bound = max_frequency * TERM_FREQUENCY_UPPER_BOUND
        lower_bound = max_frequency * TERM_FREQUENCY_LOWER_BOUND
        logging.info(f'Filtering terms by lower bound ({lower_bound}) and upper bound ({upper_bound}) for frequency')
        terms_to_keep = set()
        lower_bound_hurt, upper_bound_hurt = 0, 0
        for term, frequency in term_frequency:
            if lower_bound > frequency:
                lower_bound_hurt += 1
                continue
            if upper_bound < frequency:
                upper_bound_hurt += 1
                continue
            terms_to_keep.add(term)
        logging.info(f'{lower_bound_hurt} appear less frequent than {lower_bound} '
                     f'and {upper_bound_hurt} more than {upper_bound}')
        logging.info(f'Keeping only {len(terms_to_keep)} out of {len(term_frequency)} terms')
        logging.info('Computing final index...')
        for term, docs in term_index_local.items():
            if term in terms_to_keep:
                self.term_index[term] = docs

        logging.info(f'Term index with {len(self.term_index)} keys created')

    def create_data_graph(self):
        session = SessionExtended.get()
        self.__create_entity_index(session)
        self.__create_graph_index(session)
        self.__create_term_index(session)

    def compute_query(self, query: Query):
        document_ids = set()
        for idx, (s, p, o) in enumerate(query.statements):
            # for the first element, set all document ids as current set
            if idx == 0:
                document_ids = self.get_document_ids_for_statement(subject_id=s, relation=p, object_id=o)
            else:
                document_ids.intersection_update(
                    self.get_document_ids_for_statement(subject_id=s, relation=p, object_id=o))
            if len(document_ids) == 0:
                return set()

        for entity_id in query.entities:
            document_ids.intersection_update(self.get_document_ids_for_entity(entity_id=entity_id))
            if len(document_ids) == 0:
                return set()

        for term in query.terms:
            document_ids.intersection_update(self.get_document_ids_for_term(term=term))
            if len(document_ids) == 0:
                return set()

        return document_ids


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

    def __init__(self):
        logging.info('Init query translation...')
        self.tagger = EntityTaggerJCDL.instance()
        self.schema_graph: SchemaGraph = SchemaGraph()
        self.data_graph: DataGraph = DataGraph()
        self.__load_data_graph()
        logging.info('Query translation ready')

    def __load_data_graph(self):
        if os.path.isfile(DATA_GRAPH_CACHE):
            logging.info(f'Loading data graph from cache: {DATA_GRAPH_CACHE}')
            with open(DATA_GRAPH_CACHE, 'rb') as f:
                self.data_graph.load_data_graph(f)
        else:
            logging.info('Creating data graph...')
            self.__create_data_graph()
            logging.info(f'Storing data graph to cache: {DATA_GRAPH_CACHE}')
            with open(DATA_GRAPH_CACHE, 'wb') as f:
                self.data_graph.dump_data_graph(f)

    def __create_data_graph(self):
        self.data_graph = DataGraph()
        self.data_graph.create_data_graph()

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
        logging.info('Term2predicate mapping: ')
        for k, v in term2predicates.items():
            logging.info(f'    {k} -> {v}')
        return term2predicates

    def __greedy_find_entity_types_variables_in_keywords(self, keywords):
        term2variables = self.__greedy_find_dict_entries_in_keywords(keywords, self.schema_graph.entity_types)
        logging.info('Term2EntityTypeVariable mapping: ')
        for k, v in term2variables.items():
            logging.info(f'    {k} -> {v}')
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
        logging.info('Term2Entity mapping: ')
        for k, v in term2entities.items():
            logging.info(f'    {k} -> {v}')

        logging.debug('--' * 60)
        logging.debug('--' * 60)
        return term2entities

    def translate_keyword_query(self, keyword_query) -> GraphQuery:
        keyword_query = keyword_query.lower().strip()
        keywords = keyword_query.split(' ')
        term2predicates = self.__greedy_find_predicates_in_keywords(keywords)
        term2variables = self.__greedy_find_entity_types_variables_in_keywords(keywords)
        term2entities = self.__greedy_find_entities_in_keywords(keywords)  #

        possible_relations = list()
        subject_ids = {s for s in term2entities.values()}
        object_ids = {o for o in term2entities.values()}

        for subject_id in subject_ids:
            for object_id in object_ids:
                for relation in self.schema_graph.relation_dict:
                    document_ids = self.data_graph.get_document_ids_for_statement(subject_id=subject_id,
                                                                                  relation=relation,
                                                                                  object_id=object_id)
                    logging.info(f'{len(document_ids)} support: {subject_ids} x {relation} x {object_id}')
                    possible_relations.append((len(document_ids), subject_id, relation, object_id))
        return GraphQuery()


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    trans = QueryTranslationToGraph()
    exit(0)
    for q in QUERIES:
        logging.info('==' * 60)
        logging.info(f'Translating query: "{q}"')
        graph_q = trans.translate_keyword_query(q)
        logging.info('==' * 60)


if __name__ == "__main__":
    main()
