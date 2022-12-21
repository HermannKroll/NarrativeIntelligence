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
from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, Document, JCDLInvertedTermIndex, \
    JCDLInvertedEntityIndex, JCDLInvertedStatementIndex
from narraint.config import PHARM_RELATION_VOCABULARY, PHARM_RELATION_CONSTRAINTS
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.query_hints import SYMMETRIC_PREDICATES, PREDICATE_EXPANSION
from narrant.entity.meshontology import MeSHOntology

TERM_FREQUENCY_UPPER_BOUND = 0.99
TERM_FREQUENCY_LOWER_BOUND = 0
TERM_MIN_LENGTH = 3


def get_document_ids_from_provenance_mappings(provenance_mapping):
    if 'PubMed' in provenance_mapping:
        document_ids = set({int(i) for i in provenance_mapping['PubMed'].keys()})
        return document_ids
    else:
        return {}


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

    def __init__(self, graph_index={}, entity_index={}, term_index={}):
        self.graph_index = graph_index
        self.entity_index = entity_index
        self.term_index = term_index
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
            # print(f'Expanded {entity_id} by {entities}')
        # Chembl Drugs
        if entity_id.startswith('CHEMBL'):
            for chembl_class in self.atc_tree.get_classes_for_chembl_id(entity_id):
                entities.add(chembl_class)
        #      print(f'Expanded {entity_id} by {entities}')
        return entities

    def get_document_ids_for_term(self, term: str) -> Set[int]:
        session = SessionExtended.get()
        q = session.query(JCDLInvertedTermIndex.document_ids).filter(JCDLInvertedTermIndex.term == term)
        # if we have a result
        for r in q:
            return ast.literal_eval(r[0])
        # otherwise empty set
        return set()

    def get_document_ids_for_entity(self, entity_id) -> Set[int]:
        session = SessionExtended.get()
        q = session.query(JCDLInvertedEntityIndex.document_ids).filter(JCDLInvertedEntityIndex.entity_id == entity_id)
        # if we have a result
        for r in q:
            return ast.literal_eval(r[0])
        # otherwise empty set
        return set()

    def get_document_ids_for_statement(self, subject_id, relation, object_id) -> Set[int]:
        session = SessionExtended.get()
        q = session.query(JCDLInvertedStatementIndex.document_ids)
        q = q.filter(JCDLInvertedStatementIndex.subject_id == subject_id)
        q = q.filter(JCDLInvertedStatementIndex.relation == relation)
        q = q.filter(JCDLInvertedStatementIndex.object_id == object_id)
        # if we have a result
        for r in q:
            return ast.literal_eval(r[0])
        # otherwise empty set
        return set()

    def __add_statement_to_index(self, subject_id, relation, object_id, document_ids):
        key = (subject_id, object_id)
        if key not in self.graph_index:
            self.graph_index[key] = {}
        if relation not in self.graph_index[key]:
            self.graph_index[key][relation] = set()
        self.graph_index[key][relation].update(document_ids)

    def __create_graph_index(self, session):
        print('Creating graph index...')
        # iterate over all extracted statements
        total = session.query(PredicationInvertedIndex).count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        q_stmt = session.query(PredicationInvertedIndex).yield_per(1000000)
        for i, r in enumerate(q_stmt):
            if i > 10000:
                break

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

                # always add associated
                if relation != "associated":
                    self.__add_statement_to_index(subject_id=subj, relation="associated",
                                                  object_id=obj, document_ids=document_ids)
                # Swap subject and object im predicate is a symmetric one
                if relation in SYMMETRIC_PREDICATES:
                    self.__add_statement_to_index(subject_id=obj, relation=relation,
                                                  object_id=subj, document_ids=document_ids)

                    # always add associated
                    if relation != "associated":
                        self.__add_statement_to_index(subject_id=subj, relation="associated",
                                                      object_id=obj, document_ids=document_ids)
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
        print(f'Graph index with {len(self.graph_index)} keys created')

    def __create_entity_index(self, session):
        print('Creating entity index...')
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

            if i > 10000:
                break

        progress.done()
        print(f'Entity index with {len(self.entity_index)} keys created')

    def __create_term_index(self, session):
        print('Creating term index...')
        # iterate over all extracted statements
        total = session.query(Document).filter(Document.collection == 'PubMed').count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        stopwords = set(nltk.corpus.stopwords.words('english'))
        trans_map = {p: ' ' for p in string.punctuation}
        translator = str.maketrans(trans_map)
        term_index_local = {}
        for i, doc in enumerate(iterate_over_all_documents_in_collection(session=session, collection='PubMed')):
            progress.print_progress(i)
            # Make it lower + replace all punctuation by ' '
            doc_text = doc.get_text_content().strip().lower()
            doc_text = doc_text.translate(translator)
            for term in doc_text.split(' '):
                if not term.strip() or len(term) <= TERM_MIN_LENGTH or term in stopwords:
                    continue
                if term not in term_index_local:
                    term_index_local[term] = set()
                term_index_local[term].add(doc.id)

            if i > 10000:
                break

        progress.done()
        print('Computing how often each term was found')
        term_frequency = list([(t, len(docs)) for t, docs in term_index_local.items()])
        max_frequency = max(t[1] for t in term_frequency)
        print(f'Most frequent term appears in {max_frequency} documents')
        upper_bound = max_frequency * TERM_FREQUENCY_UPPER_BOUND
        lower_bound = max_frequency * TERM_FREQUENCY_LOWER_BOUND
        print(f'Filtering terms by lower bound ({lower_bound}) and upper bound ({upper_bound}) for frequency')
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
        print(f'{lower_bound_hurt} appear less frequent than {lower_bound} '
              f'and {upper_bound_hurt} more than {upper_bound}')
        print(f'Keeping only {len(terms_to_keep)} out of {len(term_frequency)} terms')
        print('Computing final index...')
        for term, docs in term_index_local.items():
            if term in terms_to_keep:
                self.term_index[term] = docs

        print(f'Term index with {len(self.term_index)} keys created')

    def create_data_graph(self):
        logging.info('Creating data graph...')
        session = SessionExtended.get()
        self.__create_entity_index(session)
        self.__create_graph_index(session)
        self.__create_term_index(session)

        logging.info('==' * 60)
        logging.info('Index summary:')
        logging.info(f'Terms index with {len(self.term_index)} keys created')
        logging.info(f'Graph index with {len(self.graph_index)} keys created')
        logging.info(f'Entity index with {len(self.entity_index)} keys created')
        self.__store_data_graph()

    def __store_data_graph(self):
        logging.info('Dumping data graph to DB...')
        session = SessionExtended.get()

        logging.info('Deleting table entries: JCDLInvertedTermIndex ...')
        session.execute(delete(JCDLInvertedTermIndex))
        logging.info('Deleting table entries: JCDLInvertedEntityIndex ...')
        session.execute(delete(JCDLInvertedEntityIndex))
        logging.info('Deleting table entries: JCDLInvertedTermIndex ...')
        session.execute(delete(JCDLInvertedStatementIndex))
        logging.info('Committing...')
        session.commit()

        logging.info('Storing inverted term index values...')
        JCDLInvertedTermIndex.bulk_insert_values_into_table(session, [dict(term=t, document_ids=json.dumps(docs))
                                                                      for t, docs in self.term_index.items()],
                                                            check_constraints=False)
        logging.info('Storing inverted entity index values...')
        JCDLInvertedTermIndex.bulk_insert_values_into_table(session, [dict(entity_id=e, document_ids=json.dumps(docs))
                                                                      for e, docs in self.entity_index.items()],
                                                            check_constraints=False)
        logging.info('Storing inverted statement index values...')
        JCDLInvertedTermIndex.bulk_insert_values_into_table(session, [dict(subject_id=s,
                                                                           relation=p,
                                                                           object_id=o,
                                                                           document_ids=json.dumps(docs))
                                                                      for (s, p, o), docs in self.entity_index.items()],
                                                            check_constraints=False)
        logging.info('Finished')

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


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    data_graph = DataGraph()
    data_graph.create_data_graph()


if __name__ == "__main__":
    main()
