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
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.atc.atc_tree import ATCTree
from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationInvertedIndex, TagInvertedIndex, Document, JCDLInvertedTermIndex, \
    JCDLInvertedEntityIndex, JCDLInvertedStatementIndex
from narraint.queryengine.query_hints import SYMMETRIC_PREDICATES, PREDICATE_EXPANSION
from narrant.entity.meshontology import MeSHOntology

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

    def get_query_part_without_variables(self):
        if len(self.variables) == 0:
            return Query(query=self)

        q_copy = Query(query=self)
        var_names = {v.name for v in self.variables}
        for e in self.entities:
            if e in var_names:
                q_copy.remove_entity(entity=e)
        for (s, p, o) in self.statements:
            if s in var_names or o in var_names:
                q_copy.remove_statement((s, p, o))

        return q_copy

    def get_query_part_with_variables(self):
        if len(self.variables) == 0:
            return Query(query=self)

        q_copy = Query(query=self)
        var_names = {v.name for v in self.variables}
        for e in self.entities:
            if e not in var_names:
                q_copy.remove_entity(entity=e)
        for (s, p, o) in self.statements:
            if s not in var_names and o not in var_names:
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
        self.entities.add(entity_id)
        self.entity2support[entity_id] = support
        self.entity_support = sum([s for s in self.entity2support.values()])

    def add_statement(self, subject_id, relation, object_id, support=0):
        key = (subject_id, relation, object_id)
        self.statements.add(key)
        self.statement2support[key] = support
        self.statement_support = sum([s for s in self.statement2support.values()])

    def add_relation(self, relation):
        self.relations.add(relation)

    def add_variable(self, variable: QueryVariable):
        self.variables.add(variable)

    def __str__(self):
        # term_str = '{' + f'{'), ('.join([str(term)  support for term, support in self.term2support.items()]}' + '}'
        return f'<Terms: {self.term2support} AND Entities: {self.entity2support} AND Relations: {self.relations} ' \
               f'AND Variables: {self.variables} AND Statements: {self.statement2support}>'

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.__str__())

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

    def is_non_empty(self):
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


def get_document_ids_from_provenance_mappings(provenance_mapping):
    if 'PubMed' in provenance_mapping:
        document_ids = set({int(i) for i in provenance_mapping['PubMed'].keys()})
        return document_ids
    else:
        return {}


class DataGraph:

    def __init__(self, graph_index={}, entity_index={}, term_index={}):
        self.graph_index = graph_index
        self.entity_index = entity_index
        self.term_index = term_index
        self.entity_tagger = EntityTaggerJCDL.instance()
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

    def get_document_ids_for_entity_with_variable(self, variable: QueryVariable):
        session = SessionExtended.get()
        allowed_entities = self.get_allowed_entities_for_entity_type(variable.entity_type)

        q = session.query(JCDLInvertedEntityIndex.document_ids, JCDLInvertedEntityIndex.entity_id)
        q = q.filter(JCDLInvertedEntityIndex.entity_id.in_(allowed_entities))

        varsub2docs = {variable.name: {}}
        for r in q:
            result, entity_id = ast.literal_eval(r[0]), r[1]
            varsub2docs[variable.name][entity_id] = result
        return varsub2docs

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

    def get_allowed_entities_for_entity_type(self, entity_type):
        return self.entity_tagger.entity_type2entities[entity_type]

    def get_document_ids_for_statement_with_variable(self, q_subject, relation, q_object):
        session = SessionExtended.get()

        q = session.query(JCDLInvertedStatementIndex.document_ids,
                          JCDLInvertedStatementIndex.subject_id,
                          JCDLInvertedStatementIndex.object_id)

        q = q.filter(JCDLInvertedStatementIndex.relation == relation)
        varname2type = {}
        if isinstance(q_subject, str):
            q = q.filter(JCDLInvertedStatementIndex.subject_id == q_subject)
        elif isinstance(q_subject, QueryVariable):
            allowed_subjects = self.get_allowed_entities_for_entity_type(q_subject.entity_type)
            varname2type[q_subject.name] = 'subject'
            q = q.filter(JCDLInvertedStatementIndex.subject_id.in_(allowed_subjects))

        if isinstance(q_subject, str):
            q = q.filter(JCDLInvertedStatementIndex.object_id == q_object)
        elif isinstance(q_subject, QueryVariable):
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

    def create_data_graph(self):
        print('Creating data graph and dumping it to DB...')
        session = SessionExtended.get()
        self.__create_term_index(session)
        print('Deleting table entries: JCDLInvertedTermIndex ...')
        session.execute(delete(JCDLInvertedTermIndex))
        print('Committing...')
        session.commit()

        print('Storing inverted term index values...')
        JCDLInvertedTermIndex.bulk_insert_values_into_table(session, [dict(term=t, document_ids=str(docs))
                                                                      for t, docs in self.term_index.items()],
                                                            check_constraints=False)
        self.term_index = {}

        self.__create_entity_index(session)
        print('Deleting table entries: JCDLInvertedEntityIndex ...')
        session.execute(delete(JCDLInvertedEntityIndex))
        print('Committing...')
        session.commit()
        print('Storing inverted entity index values...')
        JCDLInvertedEntityIndex.bulk_insert_values_into_table(session,
                                                              [dict(entity_id=e, document_ids=str(docs))
                                                               for e, docs in self.entity_index.items()],
                                                              check_constraints=False)
        self.entity_index = {}

        print('Deleting table entries: JCDLInvertedTermIndex ...')
        session.execute(delete(JCDLInvertedStatementIndex))
        print('Committing...')
        session.commit()
        self.__create_graph_index(session)
        print('Storing inverted statement index values...')
        JCDLInvertedStatementIndex.bulk_insert_values_into_table(session, [dict(subject_id=s,
                                                                                relation=p,
                                                                                object_id=o,
                                                                                document_ids=str(docs))
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
        for v_name in var_names:
            if v_name in varsub2docs_new:
                shared_subs = set(varsub2docs[v_name].keys()).intersection(varsub2docs_new[v_name].keys())
                for sub in shared_subs:
                    varsub2docs[v_name] = {sub: varsub2docs[v_name][sub].intersection(varsub2docs_new[v_name][sub])}

        return varsub2docs

    def compute_query(self, query: Query):
        # easy and fast mode without variables
        if len(query.variables) == 0:
            return self.compute_query_without_variables(query)

        # Compute the result ids for the query without variables
        qwo = query.get_query_part_without_variables()
        document_ids = set()
        if qwo.is_non_empty():
            document_ids = self.compute_query_without_variables(qwo)
            # Query does not yield results
            if len(document_ids) == 0:
                return {}

        # Get the query part with variables
        q_w_v = query.get_query_part_with_variables()
        # if is empty, we are finished
        if not q_w_v.is_non_empty():
            return document_ids

        # Either the qwo part is empty or has result in an non-empty document result
        var_names = {v.name for v in query.variables}
        varname2variable = {v.name: v for v in query.variables}
        document_ids = set()
        varsub2docs = {}
        for idx, (s, p, o) in enumerate(query.statements):
            # Translate subject or object into a query variable if necessary
            if s in varname2variable:
                s = varname2variable[s]
            if o in varname2variable:
                o = varname2variable[o]

            # for the first element, set all document ids as current set
            if not qwo.is_non_empty() and idx == 0:
                varsub2docs = self.get_document_ids_for_statement_with_variable(q_subject=s, relation=p, q_object=o)
            else:
                varsub2docs_new = self.get_document_ids_for_statement_with_variable(q_subject=s, relation=p, q_object=o)
                DataGraph.merge_variable_substitutions(var_names, varsub2docs, varsub2docs_new)

        for idx, entity_id in enumerate(query.entities):
            # it must be a variable
            variable = varname2variable[entity_id]
            # for the first element, set all document ids as current set
            if qwo.is_non_empty() and len(query.statements) == 0 and idx == 0:
                varsub2docs = self.get_document_ids_for_entity_with_variable(variable=variable)
            else:
                varsub2docs_new = self.get_document_ids_for_entity_with_variable(variable=variable)
                DataGraph.merge_variable_substitutions(var_names, varsub2docs, varsub2docs_new)

        # Reduce all variable subs to the set of document ids
        final_document_results = set()
        for v_name in var_names:
            for sub in varsub2docs[v_name]:
                varsub2docs[v_name][sub] = varsub2docs[v_name][sub].intersection(document_ids)
                final_document_results.update(varsub2docs[v_name][sub])

        return final_document_results


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    data_graph = DataGraph()
    data_graph.create_data_graph()


if __name__ == "__main__":
    main()
