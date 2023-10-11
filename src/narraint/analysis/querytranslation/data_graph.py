import argparse
import ast
import itertools
import json
import logging
import string
from typing import Set

import nltk
from sqlalchemy import delete

from kgextractiontoolbox.backend.models import Tag
from kgextractiontoolbox.backend.retrieve import iterate_over_all_documents_in_collection
from kgextractiontoolbox.progress import Progress
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, Document, JCDLInvertedTermIndex, \
    JCDLInvertedEntityIndex, JCDLInvertedStatementIndex, JCDLStatementSupport, JCDLEntitySupport, JCDLTermSupport, \
    Predication
from narraint.config import QUERY_YIELD_PER_K
from narrant.cleaning.pharmaceutical_vocabulary import PREDICATE_EXPANSION, SYMMETRIC_PREDICATES
from narrant.entity.entityresolver import GeneResolver
from narrant.entity.meshontology import MeSHOntology
from narrant.preprocessing.enttypes import GENE

TERM_FREQUENCY_UPPER_BOUND = 0.99
TERM_FREQUENCY_LOWER_BOUND = 0

PUNCTUATION = string.punctuation


class QueryVariable:

    def __init__(self, name, entity_type):
        self.name = name
        self.entity_type = entity_type

    def __str__(self):
        return f'?{self.name}({self.entity_type})'

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        if self.name == other.name and self.entity_type == other.entity_type:
            return True
        return False


class Query:

    def __init__(self, query=None):
        self.terms = set()
        self.term2support = {}
        self.term_support = 0

        self.entities = set()
        self.entity2support = {}
        self.entity_support = 0

        self.statements = set()
        self.statement2support = {}
        self.statement_support = 0

        self.relations = set()
        self.variables = set()

        if query:
            self.terms = query.terms.copy()
            self.term2support = query.term2support.copy()
            self.term_support = query.term_support

            self.entities = query.entities.copy()
            self.entity2support = query.entity2support.copy()
            self.entity_support = query.entity_support

            self.statements = query.statements.copy()
            self.statement2support = query.statement2support.copy()
            self.statement_support = query.statement_support

            self.relations = query.relations.copy()
            self.variables = query.variables.copy()

    @staticmethod
    def relax_query(query, delete_operations: int):
        if delete_operations == 0:
            yield None

        # Iterate over all terms and remove a term
        for term in query.terms:
            q_rel = Query(query)
            q_rel.remove_term(term)
            # if we have a single delete operation -> just yield the removed query
            if delete_operations == 1:
                yield q_rel
            # Otherwise recursively call the method again to produce all options
            elif delete_operations > 1:
                yield from Query.relax_query(q_rel, delete_operations=delete_operations - 1)

        # Iterate over all enities and remove an entity
        for entity in query.entities:
            q_rel = Query(query)
            q_rel.remove_entity(entity)
            # We have to remove all statements with that entity
            for s, p, o in query.statements:
                if s == entity or o == entity:
                    q_rel.remove_statement((s, p, o))

            # if we have a single delete operation -> just yield the removed query
            if delete_operations == 1:
                yield q_rel
            # Otherwise recursively call the method again to produce all options
            elif delete_operations > 1:
                yield from Query.relax_query(q_rel, delete_operations=delete_operations - 1)

        # Iterate over all statements and remove a statement
        for statement in query.statements:
            q_rel = Query(query)
            q_rel.remove_statement(statement)
            # if we have a single delete operation -> just yield the removed query
            if delete_operations == 1:
                yield q_rel
            # Otherwise recursively call the method again to produce all options
            elif delete_operations > 1:
                yield from Query.relax_query(q_rel, delete_operations=delete_operations - 1)

    def get_minimum_support(self):
        return min([self.term_support, self.entity_support, self.statement_support])

    def get_query_part_without_variables(self):
        if len(self.variables) == 0:
            return Query(query=self)

        q_copy = Query(query=self)
        var_names = {v.name for v in self.variables}
        for e in self.entities:
            if isinstance(e, QueryVariable):
                q_copy.remove_entity(entity=e)
        for (s, p, o) in self.statements:
            if isinstance(s, QueryVariable) or isinstance(o, QueryVariable):
                q_copy.remove_statement((s, p, o))

        return q_copy

    def get_query_part_with_variables(self):
        if len(self.variables) == 0:
            return Query(query=self)

        q_copy = Query(query=self)
        var_names = {v.name for v in self.variables}
        for e in self.entities:
            if not isinstance(e, QueryVariable):
                q_copy.remove_entity(entity=e)
        for (s, p, o) in self.statements:
            if not isinstance(s, QueryVariable) and not isinstance(o, QueryVariable):
                q_copy.remove_statement((s, p, o))

        return q_copy

    def remove_term(self, term):
        self.terms.remove(term)
        del self.term2support[term]
        self.term_support = sum([s for s in self.term2support.values()])

    def remove_entity(self, entity):
        self.entities.remove(entity)
        del self.entity2support[entity]
        self.entity_support = sum([s for s in self.entity2support.values()])

    def remove_statement(self, statement):
        self.statements.remove(statement)
        del self.statement2support[statement]
        self.statement_support = sum([s for s in self.statement2support.values()])

    def is_valid(self, verbose=False):
        # Relation should be contained, but is not => not valid
        if len(self.relations) > 0 and len(self.statements) == 0:
            if verbose: print(f'{self} not valid')
            return False
        # Not all relations are contained => not valid
        if len(self.relations) > 0 and len(self.relations.intersection({p for _, p, _ in self.statements})) != len(
                self.relations):
            if verbose: print(f'{self} not valid')
            return False
        # Otherwise valid
        if verbose: print(f'{self} valid')
        return True

    def add_term(self, term, support=0):
        if term.strip():
            self.terms.add(term)
            self.term2support[term] = support
            self.term_support = sum([s for s in self.term2support.values()])

    def add_entity(self, entity_id, support=0):
        if isinstance(entity_id, QueryVariable):
            self.__add_variable(entity_id)
        self.entities.add(entity_id)
        self.entity2support[entity_id] = support
        self.entity_support = sum([s for s in self.entity2support.values()])

    def add_statement(self, subject_id, relation, object_id, support=0):
        if isinstance(subject_id, QueryVariable):
            self.__add_variable(subject_id)
        if isinstance(object_id, QueryVariable):
            self.__add_variable(object_id)

        key = (subject_id, relation, object_id)
        self.statements.add(key)
        self.statement2support[key] = support
        self.statement_support = sum([s for s in self.statement2support.values()])

    def add_relation(self, relation):
        self.relations.add(relation)

    def __add_variable(self, variable: QueryVariable):
        self.variables.add(variable)

    def __str__(self):
        # term_str = '{' + f'{'), ('.join([str(term)  support for term, support in self.term2support.items()]}' + '}'
        return f'<Terms: {self.term2support} AND Entities: {self.entity2support} AND Relations: {self.relations} ' \
               f'AND Variables: {self.variables} AND Statements: {self.statement2support}>'

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        unique_str = f'<Terms: {sorted([t for t in self.term2support])}' \
                     f' AND Entities: {sorted([et for et in self.entity2support])}' \
                     f' AND Relations: {sorted([r for r in self.relations])}' \
                     f' AND Variables: {sorted([v for v in self.variables])}' \
                     f' AND Statements: {sorted([s for s in self.statement2support])}>'
        return hash(unique_str)

    def __eq__(self, other):
        if len(self.terms) != len(other.terms) or len(self.entities) != len(other.entities) or len(
                self.statements) != len(other.statements) or len(self.relations) != len(other.relations):
            return False
        if len(self.variables) != len(other.variables):
            return False
        if len(self.terms.intersection(other.terms)) != len(self.terms):
            return False
        if len(self.entities.intersection(other.entities)) != len(self.entities):
            return False
        if len(self.statements.intersection(other.statements)) != len(self.statements):
            return False
        if len(self.relations.intersection(other.relations)) != len(self.relations):
            return False
        if len(self.variables.intersection(other.variables)) != len(self.variables):
            return False

        return True

    def is_empty(self):
        if len(self.terms) > 0:
            return False
        if len(self.entities) > 0:
            return False
        if len(self.statements) > 0:
            return False
        return True

    def __ge__(self, other):
        if str(self) >= str(other):
            return True
        return False


class DataGraph:

    def __init__(self, graph_index={}, entity_index={}, term_index={}, document_collection=None):
        self.graph_index = graph_index
        self.entity_index = entity_index
        self.term_index = term_index
        self.entity_tagger = EntityTaggerJCDL.instance()
        self.mesh_ontology = None
        self.atc_tree = None
        self.generesolver = None
        self.document_collection = document_collection
        self.__cache_term = {}
        self.__cache_term_support = {}
        self.__cache_entity = {}
        self.__cache_entity_support = {}
        self.__cache_statement = {}
        self.__cache_statement_support = {}
        self.__entity_index_missing_entity_ids = set()
        self.__entity_index_cache = {}

    def get_support_for_term(self, term: str) -> int:
        if term in self.__cache_term_support:
            return self.__cache_term_support[term]

        session = SessionExtended.get()
        q = session.query(JCDLTermSupport.support).filter(JCDLTermSupport.term == term)
        if self.document_collection:
            q = q.filter(JCDLTermSupport.document_collection == self.document_collection)
        # if we have a result
        support = 0
        for r in q:
            support = int(r[0])

        if len(term) > 3 and term[-1] == 's':
            q = session.query(JCDLTermSupport.support).filter(JCDLTermSupport.term == term[:-1])
            if self.document_collection:
                q = q.filter(JCDLTermSupport.document_collection == self.document_collection)
            for r in q:
                support += r[0]

        self.__cache_term_support[term] = support
        return support

    def get_document_ids_for_term(self, term: str) -> Set[int]:
        if term in self.__cache_term:
            return self.__cache_term[term]

        session = SessionExtended.get()
        q = session.query(JCDLInvertedTermIndex.document_ids).filter(JCDLInvertedTermIndex.term == term)
        if self.document_collection:
            q = q.filter(JCDLInvertedTermIndex.document_collection == self.document_collection)
        # if we have a result
        result = set()
        for r in q:
            result = ast.literal_eval(r[0])

        if len(term) > 3 and term[-1] == 's':
            q = session.query(JCDLInvertedTermIndex.document_ids).filter(JCDLInvertedTermIndex.term == term[:-1])
            if self.document_collection:
                q = q.filter(JCDLInvertedTermIndex.document_collection == self.document_collection)
            for r in q:
                result.update(ast.literal_eval(r[0]))

        self.__cache_term[term] = result
        return result

    def get_support_for_entity(self, entity_id) -> int:
        if entity_id in self.__cache_entity_support:
            return self.__cache_entity_support[entity_id]

        session = SessionExtended.get()
        q = session.query(JCDLEntitySupport.support).filter(JCDLEntitySupport.entity_id == entity_id)
        if self.document_collection:
            q = q.filter(JCDLEntitySupport.document_collection == self.document_collection)
        support = 0
        for r in q:
            support = int(r[0])

        self.__cache_entity_support[entity_id] = support
        return support

    def get_document_ids_for_entity(self, entity_id) -> Set[int]:
        if entity_id in self.__cache_entity:
            return self.__cache_entity[entity_id]

        session = SessionExtended.get()
        q = session.query(JCDLInvertedEntityIndex.document_ids).filter(JCDLInvertedEntityIndex.entity_id == entity_id)
        if self.document_collection:
            q = q.filter(JCDLInvertedEntityIndex.document_collection == self.document_collection)
        # if we have a result
        result = set()
        for r in q:
            result = ast.literal_eval(r[0])

        self.__cache_entity[entity_id] = result
        return result

    def get_document_ids_for_entity_with_variable(self, variable: QueryVariable):
        session = SessionExtended.get()
        allowed_entities = self.get_allowed_entities_for_entity_type(variable.entity_type)

        q = session.query(JCDLInvertedEntityIndex.document_ids, JCDLInvertedEntityIndex.entity_id)
        q = q.filter(JCDLInvertedEntityIndex.entity_id.in_(allowed_entities))
        if self.document_collection:
            q = q.filter(JCDLInvertedEntityIndex.document_collection == self.document_collection)

        varsub2docs = {variable.name: {}}
        for r in q:
            result, entity_id = ast.literal_eval(r[0]), r[1]
            varsub2docs[variable.name][entity_id] = result
        return varsub2docs

    def get_support_for_statement(self, subject_id, relation, object_id) -> int:
        key = (subject_id, relation, object_id)
        if key in self.__cache_statement_support:
            return self.__cache_statement_support[key]

        session = SessionExtended.get()
        q = session.query(JCDLStatementSupport.support)
        q = q.filter(JCDLStatementSupport.subject_id == subject_id)
        q = q.filter(JCDLStatementSupport.relation == relation)
        q = q.filter(JCDLStatementSupport.object_id == object_id)
        if self.document_collection:
            q = q.filter(JCDLStatementSupport.document_collection == self.document_collection)
        # if we have a result
        support = 0
        for r in q:
            support = int(r[0])

        self.__cache_statement_support[key] = support
        return support

    def get_document_ids_for_statement(self, subject_id, relation, object_id) -> Set[int]:
        key = (subject_id, relation, object_id)
        if key in self.__cache_statement:
            return self.__cache_statement[key]

        session = SessionExtended.get()
        q = session.query(JCDLInvertedStatementIndex.document_ids)
        q = q.filter(JCDLInvertedStatementIndex.subject_id == subject_id)
        q = q.filter(JCDLInvertedStatementIndex.relation == relation)
        q = q.filter(JCDLInvertedStatementIndex.object_id == object_id)
        if self.document_collection:
            q = q.filter(JCDLInvertedStatementIndex.document_collection == self.document_collection)
        # if we have a result
        result = set()
        for r in q:
            result = ast.literal_eval(r[0])

        self.__cache_statement[key] = result
        return result

    def get_allowed_entities_for_entity_type(self, entity_type):
        return self.entity_tagger.entity_type2entities[entity_type]

    def get_document_ids_for_statement_with_variable(self, q_subject, relation, q_object):
        session = SessionExtended.get()

        q = session.query(JCDLInvertedStatementIndex.document_ids,
                          JCDLInvertedStatementIndex.subject_id,
                          JCDLInvertedStatementIndex.object_id)

        q = q.filter(JCDLInvertedStatementIndex.relation == relation)
        if self.document_collection:
            q = q.filter(JCDLInvertedStatementIndex.document_collection == self.document_collection)

        varname2type = {}
        if isinstance(q_subject, str):
            q = q.filter(JCDLInvertedStatementIndex.subject_id == q_subject)
        elif isinstance(q_subject, QueryVariable):
            allowed_subjects = self.get_allowed_entities_for_entity_type(q_subject.entity_type)
            varname2type[q_subject.name] = 'subject'
            q = q.filter(JCDLInvertedStatementIndex.subject_id.in_(allowed_subjects))

        if isinstance(q_object, str):
            q = q.filter(JCDLInvertedStatementIndex.object_id == q_object)
        elif isinstance(q_object, QueryVariable):
            allowed_objects = self.get_allowed_entities_for_entity_type(q_object.entity_type)
            varname2type[q_object.name] = 'object'
            q = q.filter(JCDLInvertedStatementIndex.object_id.in_(allowed_objects))

        varsub2result = {}
        for var_name in varname2type:
            varsub2result[var_name] = {}
        for r in q:
            result, subject_id, object_id = ast.literal_eval(r[0]), r[1], r[2]

            for var_name, so_type in varname2type.items():
                if so_type == 'subject':
                    varsub2result[var_name].update({subject_id: result})
                elif so_type == 'object':
                    varsub2result[var_name].update({object_id: result})

        return varsub2result

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
            logging.info('Using the Gene Resolver to replace gene ids by symbols')
            self.generesolver = GeneResolver()
            self.generesolver.load_index()

        # Gene IDs need a special handling
        if entity_type == GENE:
            gene_ids = {GENE}
            if ';' in entity_id:
                for g_id in entity_id.split(';'):
                    try:
                        gene_ids.update(self.generesolver.gene_id_to_symbol(g_id.strip()).lower())
                    except (KeyError, ValueError):
                        continue
            else:
                try:
                    gene_ids.add(self.generesolver.gene_id_to_symbol(entity_id).lower())
                except (KeyError, ValueError):
                    pass
            return gene_ids

        key = (entity_id, entity_type)
        if key in self.__entity_index_cache:
            return self.__entity_index_cache[key]

        entities = {entity_id, entity_type}

        # only MeSH has an ontology for now
        if entity_id.startswith('MESH:D'):
            mesh_desc = entity_id.replace('MESH:', '')
            try:
                for super_entity, _ in self.mesh_ontology.retrieve_superdescriptors(mesh_desc):
                    entities.add(f'MESH:{super_entity}')
            except KeyError:
                self.__entity_index_missing_entity_ids.add(mesh_desc)
                pass
            # print(f'Expanded {entity_id} by {entities}')
        # Chembl Drugs
        if entity_id.startswith('CHEMBL'):
            for chembl_class in self.atc_tree.get_classes_for_chembl_id(entity_id):
                entities.add(chembl_class)
        #      print(f'Expanded {entity_id} by {entities}')
        self.__entity_index_cache[key] = entities
        return entities

    def __add_statement_to_index(self, subject_id, relation, object_id, document_id):
        key = (subject_id, relation, object_id)
        if key not in self.graph_index:
            self.graph_index[key] = set()
        self.graph_index[key].add(int(document_id))

    def __create_graph_index(self, session, document_collection: str):
        print('Creating graph index...')
        # iterate over all extracted statements
        total = session.query(Predication)
        total = total.filter(Predication.document_collection == document_collection)
        total = total.filter(Predication.relation != None)
        total = total.count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()

        q_stmt = session.query(Predication)
        q_stmt = q_stmt.filter(Predication.document_collection == document_collection)
        q_stmt = q_stmt.filter(Predication.relation != None)
        q_stmt = q_stmt.yield_per(10000000)
        for i, r in enumerate(q_stmt):
            progress.print_progress(i)
            subjects = self.resolve_type_and_expand_entity_by_superclasses(entity_id=r.subject_id,
                                                                           entity_type=r.subject_type)
            objects = self.resolve_type_and_expand_entity_by_superclasses(entity_id=r.object_id,
                                                                          entity_type=r.object_type)
            relation = r.relation

            # Cross product between all subjects and all objects
            for subj, obj in itertools.product(subjects, objects):
                self.__add_statement_to_index(subject_id=subj, relation=relation,
                                              object_id=obj,
                                              document_id=r.document_id)

                # always add associated
                if relation != "associated":
                    self.__add_statement_to_index(subject_id=subj, relation="associated",
                                                  object_id=obj,
                                                  document_id=r.document_id)
                # Swap subject and object im predicate is a symmetric one
                if relation in SYMMETRIC_PREDICATES:
                    self.__add_statement_to_index(subject_id=obj, relation=relation,
                                                  object_id=subj,
                                                  document_id=r.document_id)

                    # always add associated
                    if relation != "associated":
                        self.__add_statement_to_index(subject_id=subj, relation="associated",
                                                      object_id=obj,
                                                      document_id=r.document_id)
                if relation in PREDICATE_EXPANSION:
                    for expanded_relation in PREDICATE_EXPANSION[relation]:
                        # Expand statement to all of its relations
                        self.__add_statement_to_index(subject_id=subj, relation=expanded_relation,
                                                      object_id=obj,
                                                      document_id=r.document_id)
                        # Is the relation symmetric again?
                        if expanded_relation in SYMMETRIC_PREDICATES:
                            self.__add_statement_to_index(subject_id=obj, relation=expanded_relation,
                                                          object_id=subj,
                                                          document_id=r.document_id)

        progress.done()
        print(f'Graph index with {len(self.graph_index)} keys created')

    def __create_entity_index(self, session, document_collection):
        print('Creating entity index...')
        # iterate over all extracted statements
        tag_count = session.query(Tag.document_id, Tag.ent_id, Tag.ent_type)
        tag_count = tag_count.filter(Tag.document_collection == document_collection)
        tag_count = tag_count.distinct()
        total = tag_count.count()

        progress = Progress(total=total, print_every=1000)
        progress.start_time()

        query = session.query(Tag.document_id, Tag.ent_id, Tag.ent_type)
        query = query.filter(Tag.document_collection == document_collection)
        query = query.distinct()
        query = query.yield_per(QUERY_YIELD_PER_K)

        for i, r in enumerate(query):
            progress.print_progress(i)
            for entity in self.resolve_type_and_expand_entity_by_superclasses(entity_id=r.ent_id,
                                                                              entity_type=r.ent_type):
                if entity not in self.entity_index:
                    self.entity_index[entity] = set()
                self.entity_index[entity].add(int(r.document_id))

        progress.done()
        if len(self.__entity_index_missing_entity_ids) > 0:
            print(f'Could not find supertypes for MeSH Descriptors: {self.__entity_index_missing_entity_ids}')
        print(f'Entity index with {len(self.entity_index)} keys created (collection = {document_collection})')

    def __create_term_index(self, session, document_collection: str):
        print('Creating term index...')
        # iterate over all extracted statements
        total = session.query(Document).filter(Document.collection == document_collection).count()
        progress = Progress(total=total, print_every=1000)
        progress.start_time()
        stopwords = set(nltk.corpus.stopwords.words('english'))
        trans_map = {p: ' ' for p in PUNCTUATION}
        translator = str.maketrans(trans_map)
        term_index_local = {}
        for i, doc in enumerate(
                iterate_over_all_documents_in_collection(session=session, collection=document_collection,
                                                         consider_sections=True)):

            progress.print_progress(i)
            # Make it lower + replace all punctuation by ' '
            doc_text = doc.get_text_content(sections=True).strip().lower()
            # To this with and without punctuation removal
            doc_text_without_punctuation = doc_text.translate(translator)
            for term in itertools.chain(doc_text.split(' '), doc_text_without_punctuation.split(' ')):
                term = term.strip()
                if not term or term in stopwords:
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

    def create_data_graph(self, document_collections: [str] = None):
        print('Creating data graph and dumping it to DB...')
        session = SessionExtended.get()
        if document_collections:
            print(f'Deleting table entries: JCDLInvertedTermIndex and JCDLTermSupport for collections: '
                  f'{document_collections}')
            session.execute(delete(JCDLInvertedTermIndex)
                            .where(JCDLInvertedTermIndex.document_collection.in_(document_collections)))
            session.execute(delete(JCDLTermSupport.
                                   where(JCDLTermSupport.document_collection.in_(document_collections))))

            print(f'\nDeleting table entries: JCDLInvertedEntityIndex and JCDLEntitySupport for collections: '
                  f'{document_collections}')
            session.execute(delete(JCDLInvertedEntityIndex
                                   .where(JCDLInvertedEntityIndex.document_collection.in_(document_collections))))
            session.execute(delete(JCDLEntitySupport
                                   .where(JCDLEntitySupport.document_collection.in_(document_collections))))

            print('\nDeleting table entries: JCDLInvertedTermIndex and JCDLStatementSupport for collections: '
                  f'{document_collections}')
            session.execute(delete(JCDLInvertedStatementIndex
                                   .where(JCDLInvertedStatementIndex.document_collection.in_(document_collections))))
            session.execute(delete(JCDLStatementSupport
                                   .where(JCDLStatementSupport.document_collection.in_(document_collections))))

        else:
            print('Deleting table entries: JCDLInvertedTermIndex and JCDLTermSupport...')
            session.execute(delete(JCDLInvertedTermIndex))
            session.execute(delete(JCDLTermSupport))

            print('\nDeleting table entries: JCDLInvertedEntityIndex and JCDLEntitySupport...')
            session.execute(delete(JCDLInvertedEntityIndex))
            session.execute(delete(JCDLEntitySupport))

            print('\nDeleting table entries: JCDLInvertedTermIndex and JCDLStatementSupport ...')
            session.execute(delete(JCDLInvertedStatementIndex))
            session.execute(delete(JCDLStatementSupport))

        print('Committing...')
        session.commit()

        if not document_collections:
            logging.info('\nComputing document collections...')
            document_collections = set([r[0] for r in session.query(Document.collection).distinct()])
            logging.info(f'Iterate over the following collections: {document_collections}')

        for collection in document_collections:
            print(f'Computing term index for: {collection}')
            self.__create_term_index(session, document_collection=collection)
            print('Storing inverted term index values...')
            JCDLInvertedTermIndex.bulk_insert_values_into_table(session, [dict(term=t, document_collection=collection,
                                                                               document_ids=str(docs))
                                                                          for t, docs in self.term_index.items()])

            JCDLTermSupport.bulk_insert_values_into_table(session, [dict(term=t, document_collection=collection,
                                                                         support=len(docs))
                                                                    for t, docs in self.term_index.items()])

            self.term_index = {}

        for collection in document_collections:
            print(f'Computing entity index for: {collection}')
            self.__create_entity_index(session, document_collection=collection)
            print('Storing inverted entity index values...')
            JCDLInvertedEntityIndex.bulk_insert_values_into_table(session,
                                                                  [dict(entity_id=e, document_collection=collection,
                                                                        document_ids=str(docs))
                                                                   for e, docs in self.entity_index.items()],
                                                                  check_constraints=False)

            JCDLEntitySupport.bulk_insert_values_into_table(session,
                                                            [dict(entity_id=e, document_collection=collection,
                                                                  support=len(docs))
                                                             for e, docs in self.entity_index.items()],
                                                            check_constraints=False)
            self.entity_index = {}

        for collection in document_collections:
            self.__create_graph_index(session, document_collection=collection)
            print('Storing inverted statement index values...')
            JCDLInvertedStatementIndex.bulk_insert_values_into_table(session, [dict(subject_id=s,
                                                                                    relation=p,
                                                                                    object_id=o,
                                                                                    document_collection=collection,
                                                                                    document_ids=str(docs))
                                                                               for (s, p, o), docs in
                                                                               self.graph_index.items()],
                                                                     check_constraints=False)

            JCDLStatementSupport.bulk_insert_values_into_table(session, [dict(subject_id=s,
                                                                              relation=p,
                                                                              object_id=o,
                                                                              document_collection=collection,
                                                                              support=len(docs))
                                                                         for (s, p, o), docs in
                                                                         self.graph_index.items()],
                                                               check_constraints=False)

        self.graph_index = {}
        print('Finished')

    def compute_query_without_variables(self, query: Query):
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

    @staticmethod
    def merge_variable_substitutions(var_names, varsub2docs, varsub2docs_new):
        varsub2docs_result = {}
        for v_name in var_names:
            varsub2docs_result[v_name] = {}
            if v_name in varsub2docs_new:
                shared_subs = set(varsub2docs[v_name].keys()).intersection(set(varsub2docs_new[v_name].keys()))
                for sub in shared_subs:
                    varsub2docs_result[v_name][sub] = varsub2docs[v_name][sub].intersection(
                        varsub2docs_new[v_name][sub])
            else:
                for sub in varsub2docs[v_name]:
                    varsub2docs_result[v_name][sub] = varsub2docs[v_name][sub]
        return varsub2docs_result

    def compute_query(self, query: Query):
        # easy and fast mode without variables
        if len(query.variables) == 0:
            return self.compute_query_without_variables(query)

        # Compute the result ids for the query without variables
        qwo = query.get_query_part_without_variables()
        print(qwo)
        document_ids = set()
        if not qwo.is_empty():
            print('qwo non empty')
            document_ids = self.compute_query_without_variables(qwo)
            # Query does not yield results
            if len(document_ids) == 0:
                return {}

        # Get the query part with variables
        q_w_v = query.get_query_part_with_variables()
        print(q_w_v)
        # if is empty, we are finished
        if q_w_v.is_empty():
            return document_ids

        # Either the qwo part is empty or has result in an non-empty document result
        var_names = {v.name for v in query.variables}
        varname2variable = {v.name: v for v in query.variables}
        document_ids = set()
        varsub2docs = {}
        for idx, (s, p, o) in enumerate(query.statements):
            # Translate subject or object into a query variable if necessary
            #  if s in varname2variable:
            #      s = varname2variable[s]
            #  if o in varname2variable:
            #     o = varname2variable[o]

            # for the first element, set all document ids as current set
            if qwo.is_empty() and idx == 0:
                varsub2docs = self.get_document_ids_for_statement_with_variable(q_subject=s, relation=p, q_object=o)
            else:
                varsub2docs_new = self.get_document_ids_for_statement_with_variable(q_subject=s, relation=p, q_object=o)
                varsub2docs = DataGraph.merge_variable_substitutions(var_names, varsub2docs, varsub2docs_new)

        for idx, entity_var in enumerate(query.entities):
            # it must be a variable
            # variable = varname2variable[entity_id]
            # for the first element, set all document ids as current set
            if qwo.is_empty() and len(query.statements) == 0 and idx == 0:
                varsub2docs = self.get_document_ids_for_entity_with_variable(variable=entity_var)
            else:
                varsub2docs_new = self.get_document_ids_for_entity_with_variable(variable=entity_var)
                varsub2docs = DataGraph.merge_variable_substitutions(var_names, varsub2docs, varsub2docs_new)

        # Reduce all variable subs to the set of document ids
        final_document_results = set()
        for v_name in var_names:
            for sub in varsub2docs[v_name]:
                # If we do not have a filter
                if len(document_ids) > 0:
                    varsub2docs[v_name][sub] = varsub2docs[v_name][sub].intersection(document_ids)
                final_document_results.update(varsub2docs[v_name][sub])

        return final_document_results


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--collections", default=None, nargs="+", help="Document collection to update")
    args = parser.parse_args()

    print(f'Will process the following collections: {args.collections}')
    print('Should I continue? y/yes to continue')
    uin = input().lower()
    if uin == "yes" or uin == "y":
        # we just want to create
        data_graph = DataGraph()
        data_graph.create_data_graph(document_collections=args.collections)
    else:
        print('Ok. Will stop here.')


if __name__ == "__main__":
    main()
