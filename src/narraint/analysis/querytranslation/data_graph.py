import ast
import itertools
import json
import logging
import string
from typing import Set

import nltk
from sqlalchemy import delete

from kgextractiontoolbox.backend.retrieve import iterate_over_all_documents_in_collection
from kgextractiontoolbox.progress import Progress
from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, Document, JCDLInvertedTermIndex, \
    JCDLInvertedEntityIndex, JCDLInvertedStatementIndex
from narraint.queryengine.query_hints import SYMMETRIC_PREDICATES, PREDICATE_EXPANSION
from narrant.entity.meshontology import MeSHOntology

TERM_FREQUENCY_UPPER_BOUND = 0.99
TERM_FREQUENCY_LOWER_BOUND = 0

PUNCTUATION = string.punctuation  # without - / +
PUNCTUATION = PUNCTUATION.replace('-', '')
PUNCTUATION = PUNCTUATION.replace('+', '')


def get_document_ids_from_provenance_mappings(provenance_mapping):
    if 'PubMed' in provenance_mapping:
        document_ids = set({int(i) for i in provenance_mapping['PubMed'].keys()})
        return document_ids
    else:
        return {}


class Query:

    def __init__(self, query=None):
        self.terms = set()
        self.entities = set()
        self.statements = set()

        if query:
            self.terms = query.terms.copy()
            self.entities = query.entities.copy()
            self.statements = query.statements.copy()

    def add_term(self, term):
        if term.strip():
            self.terms.add(term)

    def add_entity(self, entity_id):
        self.entities.add(entity_id)

    def add_statement(self, subject_id, relation, object_id):
        self.statements.add((subject_id, relation, object_id))

    def __str__(self):
        return f'<Terms: {self.terms} AND Entities: {self.entities} AND Statements: {self.statements}>'

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        if len(self.terms) != len(other.terms) or len(self.entities) != len(other.entities) or len(
                self.statements) != len(other.statements):
            return False
        if len(self.terms.intersection(other.terms)) != len(self.terms):
            return False
        if len(self.entities.intersection(other.entities)) != len(self.entities):
            return False
        if len(self.statements.intersection(other.statements)) != len(self.statements):
            return False
        return True

    def __ge__(self, other):
        if str(self) >= str(other):
            return True
        return False


class DataGraph:

    def __init__(self, graph_index={}, entity_index={}, term_index={}):
        self.graph_index = graph_index
        self.entity_index = entity_index
        self.term_index = term_index
        self.mesh_ontology = None
        self.atc_tree = None
        self.__cache_term = {}
        self.__cache_entity = {}
        self.__cache_statement = {}

    def get_document_ids_for_term(self, term: str) -> Set[int]:
        if term in self.__cache_term:
            return self.__cache_term[term]

        session = SessionExtended.get()
        q = session.query(JCDLInvertedTermIndex.document_ids).filter(JCDLInvertedTermIndex.term == term)
        # if we have a result
        result = set()
        for r in q:
            result = ast.literal_eval(r[0])

        self.__cache_term[term] = result
        return result

    def get_document_ids_for_entity(self, entity_id) -> Set[int]:
        if entity_id in self.__cache_entity:
            return self.__cache_entity[entity_id]

        session = SessionExtended.get()
        q = session.query(JCDLInvertedEntityIndex.document_ids).filter(JCDLInvertedEntityIndex.entity_id == entity_id)
        # if we have a result
        result = set()
        for r in q:
            result = ast.literal_eval(r[0])

        self.__cache_entity[entity_id] = result
        return result

    def get_document_ids_for_statement(self, subject_id, relation, object_id) -> Set[int]:
        key = (subject_id, relation, object_id)
        if key in self.__cache_statement:
            return self.__cache_statement[key]

        session = SessionExtended.get()
        q = session.query(JCDLInvertedStatementIndex.document_ids)
        q = q.filter(JCDLInvertedStatementIndex.subject_id == subject_id)
        q = q.filter(JCDLInvertedStatementIndex.relation == relation)
        q = q.filter(JCDLInvertedStatementIndex.object_id == object_id)
        # if we have a result
        result = set()
        for r in q:
            result = ast.literal_eval(r[0])

        self.__cache_statement[key] = result
        return result

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

    def __add_statement_to_index(self, subject_id, relation, object_id, document_ids):
        key = (subject_id, relation, object_id)
        if key not in self.graph_index:
            self.graph_index[key] = set()
        self.graph_index[key].update(document_ids)

    def __create_graph_index(self, session):
        print('Creating graph index...')
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

        progress.done()
        print(f'Entity index with {len(self.entity_index)} keys created')

    def __create_term_index(self, session):
        print('Creating term index...')
        # iterate over all extracted statements
        total = session.query(Document).filter(Document.collection == 'PubMed').count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        stopwords = set(nltk.corpus.stopwords.words('english'))
        trans_map = {p: ' ' for p in PUNCTUATION}
        translator = str.maketrans(trans_map)
        term_index_local = {}
        for i, doc in enumerate(iterate_over_all_documents_in_collection(session=session, collection='PubMed')):
            progress.print_progress(i)
            # Make it lower + replace all punctuation by ' '
            doc_text = doc.get_text_content().strip().lower()
            doc_text = doc_text.translate(translator)
            for term in doc_text.split(' '):
                term = term.strip()
                if term in stopwords:
                    continue
                if term not in term_index_local:
                    term_index_local[term] = set()
                term_index_local[term].add(doc.id)

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
        print('Creating data graph...')
        session = SessionExtended.get()
        self.__create_entity_index(session)
        self.__create_graph_index(session)
        self.__create_term_index(session)

        print('==' * 60)
        print('Index summary:')
        print(f'Terms index with {len(self.term_index)} keys created')
        print(f'Graph index with {len(self.graph_index)} keys created')
        print(f'Entity index with {len(self.entity_index)} keys created')
        self.__store_data_graph()

    def __store_data_graph(self):
        print('Dumping data graph to DB...')
        session = SessionExtended.get()

        print('Deleting table entries: JCDLInvertedTermIndex ...')
        session.execute(delete(JCDLInvertedTermIndex))
        print('Deleting table entries: JCDLInvertedEntityIndex ...')
        session.execute(delete(JCDLInvertedEntityIndex))
        print('Deleting table entries: JCDLInvertedTermIndex ...')
        session.execute(delete(JCDLInvertedStatementIndex))
        print('Committing...')
        session.commit()

        print('Storing inverted term index values...')
        JCDLInvertedTermIndex.bulk_insert_values_into_table(session, [dict(term=t, document_ids=str(docs))
                                                                      for t, docs in self.term_index.items()],
                                                            check_constraints=False)
        print('Storing inverted entity index values...')
        JCDLInvertedEntityIndex.bulk_insert_values_into_table(session,
                                                              [dict(entity_id=e, document_ids=str(docs))
                                                               for e, docs in self.entity_index.items()],
                                                              check_constraints=False)
        print('Storing inverted statement index values...')
        JCDLInvertedStatementIndex.bulk_insert_values_into_table(session, [dict(subject_id=s,
                                                                                relation=p,
                                                                                object_id=o,
                                                                                document_ids=str(docs))
                                                                           for (s, p, o), docs in
                                                                           self.graph_index.items()],
                                                                 check_constraints=False)
        print('Finished')

    def compute_query(self, query: Query):
        document_ids = set()
        for idx, (s, p, o) in enumerate(query.statements):
            # for the first element, set all document ids as current set
            if idx == 0:
                document_ids = self.get_document_ids_for_statement(subject_id=s, relation=p, object_id=o)
            else:
                document_ids = document_ids.intersection(
                    self.get_document_ids_for_statement(subject_id=s, relation=p, object_id=o))
            if len(document_ids) == 0:
                return set()

        for idx, entity_id in enumerate(query.entities):
            # for the first element, set all document ids as current set
            if len(query.statements) == 0 and idx == 0:
                document_ids = self.get_document_ids_for_entity(entity_id=entity_id)
            else:
                document_ids = document_ids.intersection(self.get_document_ids_for_entity(entity_id=entity_id))
            if len(document_ids) == 0:
                return set()

        for idx, term in enumerate(query.terms):
            # for the first element, set all document ids as current set
            if len(query.statements) == 0 and len(query.entities) == 0 and idx == 0:
                document_ids = self.get_document_ids_for_term(term=term)
            else:
                document_ids = document_ids.intersection(self.get_document_ids_for_term(term=term))
            if len(document_ids) == 0:
                return set()

        return document_ids


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    data_graph = DataGraph()
    data_graph.create_data_graph()


if __name__ == "__main__":
    main()
