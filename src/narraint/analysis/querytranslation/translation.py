import itertools
import logging
from copy import copy

import nltk

from narraint.analysis.querytranslation.data_graph import DataGraph, Query
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.analysis.querytranslation.schema_graph import SchemaGraph

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

class QueryTranslationToGraph:

    def __init__(self, data_graph: DataGraph, schema_graph: SchemaGraph):
        print('Init query translation...')
        self.tagger = EntityTaggerJCDL.instance()
        self.schema_graph: SchemaGraph = schema_graph
        self.data_graph: DataGraph = data_graph
        self.stopwords = set(nltk.corpus.stopwords.words('english'))
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
        return self.__greedy_find_dict_entries_in_keywords(keywords, self.schema_graph.relation_dict)

    def __greedy_find_entity_types_variables_in_keywords(self, keywords):
        return self.__greedy_find_dict_entries_in_keywords(keywords, self.schema_graph.entity_types)

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
        #    logging.debug(f'Found entities in part: {terms_mapped}')
        #    logging.debug(f'Cannot find entities in part: {keywords_not_mapped}')
        return term2entities

    def generate_possible_queries(self, possible_terms, possible_entities, possible_statements, possible_relations,
                                  verbose=False):
        possible_queries = set()
        # Compute all possibilities which entity mappings and relation mappings we could take, i.e.,
        # [t1 -> e1, t1-> e2, t1->relation1, t2-> e3]
        # Mapping plan:
        # [t1 : [e1, e2, relation1],
        #  t2: [e2]
        # ]
        # Compute this mapping plan

        term2mapping = {}
        # consider entities
        for e_support, term, entity in possible_entities:
            if term not in term2mapping:
                term2mapping[term] = {('entity', entity, e_support)}
            else:
                term2mapping[term].add(('entity', entity, e_support))
        # consider relations
        for term, relation in possible_relations:
            if term not in term2mapping:
                term2mapping[term] = {('relation', relation, 0)}
            else:
                term2mapping[term].add(('relation', relation, 0))

        # we need a sorted list here (access must work over idx)
        term2mapping = sorted(list([(term, list(mapping)) for term, mapping in term2mapping.items()]),
                              key=lambda x: x[0])
        # Compute selection plan
        # -1 means no selection
        selection_map = list()
        for term, mapping in term2mapping:
            selection_map.append(list(range(-1, len(mapping))))

        selection_map = list(itertools.product(*selection_map))
        # print(f'Entity selection map entries: {len(selection_map)}')
        # print(term2mapping)
        # print(selection_map)

        # Then fill the qery with the remaining terms
        for select_map in selection_map:
            query = Query()
            terms_translated = list()

            for idx, s_entry in enumerate(select_map):
                # do not select
                if s_entry == -1:
                    continue
                else:
                    # select the entry
                    term = term2mapping[idx][0]
                    mapped_to = term2mapping[idx][1][s_entry]

                    terms_translated.extend(term.split(' '))
                    if mapped_to[0] == 'entity':
                        # get entity and support
                        query.add_entity(mapped_to[1], support=mapped_to[2])
                    else:
                        query.add_relation(mapped_to[1])

            # Now add all terms that are not translated
            for term_support, term in possible_terms:
                if term in terms_translated:
                    continue
                query.add_term(term, support=term_support)

            possible_queries.add(query)

        # Note: vector consisting only of 0 generates a term-based query only

        # We generated all possible queries consisting of entities and term combinations
        # Now extend these queries by adding statements between entities if possible
        # We need to know which statements can be placed between two entities:
        # Generate a structure like this
        # [
        # [(e1, r1, e2), (e1, r2, e2)],    << Possible statements between e1 and e2
        # [(e2, r1, e3)]                   << Possible statements between e2 and e3
        # ]
        #
        # Important: only place one relation between each entity pair!!
        statement_groups = {}
        for stmt_support, _, subject_id, relation, _, object_id in possible_statements:
            # Ignore direction here and have an undirected key access
            if subject_id < object_id:
                key = (subject_id, object_id)
            else:
                key = (object_id, subject_id)

            if key not in statement_groups:
                statement_groups[key] = [(subject_id, relation, object_id, stmt_support)]
            else:
                statement_groups[key].append((subject_id, relation, object_id, stmt_support))

        # We need a fixed order
        statement_groups = list([(k, v) for k, v in statement_groups.items()])

        # Next, we need to copy each generated query and extend it with our selection
        possible_queries_with_statements = set()  # we may produce duplicates - so use a set
        for q in possible_queries:
            # We need at least two entity mentions
            if len(q.entities) < 2:
                continue
            # if len(possible_queries_with_statements) > 1000000:
            #    print(f'query generation limit hit for: {possible_terms}')
            #    continue

            # We now know which statements are possible between two entities
            # We need to select every combination
            # [
            # [(e1, r1, e2), (e1, r2, e2)],    >> 3 choices possible (two options + do not select)
            # [(e2, r1, e3)]                   >> 2 choices possible (one option + do not select)
            # ]

            # Select only those statements which subject and objects are in the queries entities
            relevant_statement_groups = list([(key, stmts) for key, stmts in statement_groups
                                              if key[0] in q.entities and key[1] in q.entities])

            bitmap = list()
            estimated_combinations = 1
            for key, stmts in relevant_statement_groups:
                estimated_combinations = estimated_combinations * (len(stmts) * 2)
                bitmap.append(list(range(-1, len(stmts) - 1)))  # -1 means do not select

            # print(f'Estimated combinations: {estimated_combinations}')

            # Now generate a list of all possible selections
            bitmap = list(itertools.product(*bitmap))

            # Now iterate over all possibilies
            for b_entry in bitmap:
                # Create a copy of the query
                q_s = Query(query=q)

                for idx, (key, stmts) in enumerate(relevant_statement_groups):
                    # Entities must be included in the query - We can now add the selected statement from our bitmap
                    selected_idx = b_entry[idx]
                    if selected_idx != -1:  # -1 Means do not select
                        s, p, o, stmt_support = stmts[selected_idx]
                        # if the query forces a certain relationship then it shoud be mentioned!
                        if len(q_s.relations) > 0 and p not in q_s.relations:
                            continue

                        q_s.add_statement(subject_id=s, relation=p, object_id=o, support=stmt_support)

                # Add the newly generated query if it contains at least a single statement
                if len(q_s.statements) > 0:
                    # we may produce duplicates - so use a set
                    possible_queries_with_statements.add(q_s)

        # Add them finally to the result list
        possible_queries.update(possible_queries_with_statements)

        # Queries that contain a relation must have a certain statement, otherwise thei need to be removed
        possible_queries = {q for q in possible_queries if q.is_valid(verbose=False)}
        return possible_queries

    def translate_keyword_query(self, keyword_query, verbose=True):
        # Diabetes Melitus Metformin Type 2
        # Compute all permutations
        # Split by ' '
        # 1. Test all variants of each permutation (of t he split list)
        # 2. Take the permutation which has the longest entity mentions
        # 3. Every keyword by its own
        # Take the ntlk tokenizer
        #   doc_text = doc.get_text_content().strip().lower()
        #   doc_text = doc_text.replace('-', ' ')
        #    doc_text = doc_text.replace('/', ' ')
        #    doc_text = doc_text.translate(translator)
        #    for term in doc_text.split(' '):

        trans_map = {p: ' ' for p in '[]()?!'}  # PUNCTUATION}
        translator = str.maketrans(trans_map)

        keyword_query = keyword_query.lower().strip()
        keyword_query = keyword_query.translate(translator)
        possible_keywords = keyword_query.split(' ')
        possible_keywords = list([k for k in possible_keywords if k and k not in self.stopwords])

        keyword_generator = [possible_keywords]
        # keyword_generator = itertools.permutations(possible_keywords)

        possible_queries = list()
        for keywords in keyword_generator:
            if verbose:
                print(f'Test keyword permutation: {keywords}')
            term2predicates = self.__greedy_find_predicates_in_keywords(keywords)
            term2variables = self.__greedy_find_entity_types_variables_in_keywords(keywords)
            term2entities = self.__greedy_find_entities_in_keywords(keywords)  #

            if verbose:
                print('Term2predicate mapping: ')
                for k, v in term2predicates.items():
                    print(f'    {k} -> {v}')
                print('Term2EntityTypeVariable mapping: ')
                for k, v in term2variables.items():
                    print(f'    {k} -> {v}')
                print('Term2Entity mapping: ')
                for k, v in term2entities.items():
                    print(f'    {k} -> {v}')

            if verbose:
                print('--' * 60)
                print('Term support')
                print('--' * 60)
            possible_terms = list()
            for term in keywords:
                term = term.strip()
                # We won't find smaller terms
                if not term:
                    continue
                document_ids = self.data_graph.get_document_ids_for_term(term=term)
                if len(document_ids) > 0:
                    possible_terms.append((len(document_ids), term))
                    if verbose:
                        print(f'{len(document_ids)} support: {term}')

            if verbose:
                print('--' * 60)
                print('Entity support')
                print('--' * 60)
            possible_entities = list()
            for term, entities in term2entities.items():
                for entity in entities:
                    document_ids = self.data_graph.get_document_ids_for_entity(entity_id=entity)
                    if len(document_ids) > 0:
                        possible_entities.append((len(document_ids), term, entity))
                        if verbose:
                            print(f'{len(document_ids)} support: {term} ---> {entity}')

            if verbose:
                print('--' * 60)
                print('Statement support')
                print('--' * 60)
            possible_statements = list()
            for term1 in term2entities:
                for term2 in term2entities:
                    if term1 == term2:
                        continue
                    subject_ids = term2entities[term1]
                    object_ids = term2entities[term2]

                    for subject_id in subject_ids:
                        for object_id in object_ids:
                            for relation in self.schema_graph.relation_dict:
                                if relation in self.schema_graph.symmetric_relations:
                                    # create only one direction and not both
                                    if subject_id > object_id:
                                        continue

                                document_ids = self.data_graph.get_document_ids_for_statement(subject_id=subject_id,
                                                                                              relation=relation,
                                                                                              object_id=object_id)
                                if len(document_ids) > 0:
                                    if verbose:
                                        print(
                                            f'{len(document_ids)} support: {subject_id} ({term1}) x {relation} x {object_id} ({term2})')
                                    possible_statements.append(
                                        (len(document_ids), term1, subject_id, relation, term2, object_id))

            if verbose:
                print('--' * 60)

            # if we have possible term2relation mappings, use them
            possible_relations = list()
            for term, predicate in term2predicates.items():
                possible_relations.append((term, predicate))

            # Generate the actual queries
            possible_queries.extend(list(self.generate_possible_queries(possible_terms=possible_terms,
                                                                        possible_entities=possible_entities,
                                                                        possible_statements=possible_statements,
                                                                        possible_relations=possible_relations,
                                                                        verbose=verbose)))
            if verbose:
                print('==' * 60)
                print('Results')
                print(
                    f'{len(possible_queries)} queries generated <== ({len(possible_terms)} possible terms / {len(possible_entities)} possible entities / {len(possible_statements)} possible statements)')

        possible_queries.sort(key=lambda x: str(x), reverse=True)
        return possible_queries

    def evaluate_queries(self, queries: [Query]):
        for q in queries:
            results = len(self.data_graph.compute_query(q))
            if results > 0:
                print(f'{results} hits for {q}')


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
