import copy
import itertools
import logging
from collections import defaultdict
from datetime import datetime
from typing import List, Set, Tuple, Dict

from kgextractiontoolbox.document.narrative_document import StatementExtraction
from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.entity.query_translation import QueryTranslation
from narraint.keywords2graph.schema_support_graph import SchemaSupportGraph
from narraint.pattern_discovery.discovery import PatternDiscovery
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.query_hints import PREDICATE_ASSOCIATED, ENTITY_TYPE_VARIABLE, VAR_TYPE
from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.indexed_document import retrieve_indexed_documents_from_database_small, IndexedDocument, \
    ScoredDocumentStatement
from narraint.ranking.ranking import PublicationDateRank
from narrant.entity.entity import Entity, get_unique_entity_key
from narrant.entitylinking.enttypes import DOSAGE_FORM, TARGET, GENE

ASSOCIATED = PREDICATE_ASSOCIATED


class SupportedFactPattern:

    def __init__(self, keyword1, entity_type1, relation, keyword2, entity_type2, support):
        self.keyword1 = keyword1
        self.entity_type1 = entity_type1
        self.relation = relation
        self.keyword2 = keyword2
        self.entity_type2 = entity_type2
        self.support = support

    def is_equal(self, other):
        if not isinstance(other, SupportedFactPattern):
            return False
        s = self.keyword1 == other.keyword1 and self.entity_type1 == other.entity_type1
        r = self.relation == other.relation
        o = self.keyword2 == other.keyword2 and self.entity_type2 == other.entity_type2
        return s and r and o

    def is_flipped_equal(self, other):
        if not isinstance(other, SupportedFactPattern):
            return False
        s = self.keyword1 == other.keyword2 and self.entity_type1 == other.entity_type2
        r = self.relation == other.relation
        o = self.keyword2 == other.keyword1 and self.entity_type2 == other.entity_type1
        return s and r and o

    def __str__(self):
        return f'<{self.support}: {self.keyword1}, {self.relation}, {self.keyword2}>'

    def __repr__(self):
        return f'<{self.support}: {self.keyword1}, {self.relation}, {self.keyword2}>'


class SupportedGraphPattern:

    def __init__(self):
        self.fact_patterns: [SupportedFactPattern] = []
        self.minimum_support = 0

    def copy(self):
        g = SupportedGraphPattern()
        g.minimum_support = self.minimum_support
        g.fact_patterns = copy.copy(self.fact_patterns)
        return g

    def add_supported_fact_patterns(self, fp: SupportedFactPattern):
        if self.minimum_support == 0 and fp.support > 0:
            self.minimum_support = fp.support
        else:
            self.minimum_support = min(self.minimum_support, fp.support)

        self.fact_patterns.append(fp)

    def get_relations(self):
        return {fp.relation for fp in self.fact_patterns}

    def is_specific(self):
        return ASSOCIATED not in self.get_relations()

    def is_associated(self):
        relations = self.get_relations()
        return len(relations) == 1 and ASSOCIATED in relations

    def is_flipped_equal_to_other(self, other):
        if not isinstance(other, SupportedGraphPattern):
            return False
        if len(self.fact_patterns) != len(other.fact_patterns):
            return False
        # Iterate over all fact patterns
        # Check whether each fp has an equal pattern in other or is flipped equal to a pattern in other
        # Only if every pattern has a match, the pattern is equal
        for fp1 in self.fact_patterns:
            match = False
            for fp2 in other.fact_patterns:
                if fp1.is_equal(fp2) or fp1.is_flipped_equal(fp2):
                    match = True
                    break
            if not match:
                return False
        return True

    def to_json_data(self):
        data = []
        for fp in self.fact_patterns:
            data.append((fp.keyword1, fp.relation, fp.keyword2))
        return data


class Keyword2GraphTranslation:

    def __init__(self):
        self.graph: SchemaSupportGraph = SchemaSupportGraph()
        self.translation: QueryTranslation = QueryTranslation()
        self.discovery: PatternDiscovery = PatternDiscovery()
        self.date_ranker = PublicationDateRank()

    @staticmethod
    def greedy_find_most_supported_entity_type(entities: [Entity]):
        entity_ids = {e.entity_id for e in entities}
        entity_types = {e.entity_type for e in entities}

        session = SessionExtended.get()
        query = session.query(TagInvertedIndex.entity_id, TagInvertedIndex.entity_type, TagInvertedIndex.support)
        query = query.filter(TagInvertedIndex.entity_id.in_(entity_ids))
        query = query.filter(TagInvertedIndex.entity_type.in_(entity_types))

        # we can control the preference if entity types have the same support
        preference_dict = dict()
        preference_dict[DOSAGE_FORM] = 10

        entity2support = defaultdict(lambda: [0, 0])  # [support, preference]

        for row in query:
            entity_key = (row.entity_type, row.entity_id)
            if entity_key not in entity2support:
                entity2support[entity_key][1] = preference_dict.get(row.entity_type, 1)

            entity2support[entity_key][0] += row.support

        # Compute a sorted list
        entity_support_list = [(et, e, supp, pref) for (et, e), (supp, pref) in entity2support.items()]
        entity_support_list.sort(key=lambda x: (x[2], x[3]), reverse=True)
        logging.debug(f"{entity_support_list}")

        # Get the type of the first element
        return entity_support_list[0][0]

    def find_all_possible_query_patterns(self, keywords_with_types) -> [SupportedGraphPattern]:
        # Suppose types: A, B, C
        # We can build the following graphs:
        # ('A', 'B', 'C')
        # ('A', 'C', 'B')
        # ('B', 'A', 'C')
        # ('B', 'C', 'A')
        # ('C', 'A', 'B')
        # ('C', 'B', 'A')

        # Go through each combination and compute all possible relations between each entity types
        # Then find the minimum support of the whole pattern (less supported edge)
        final_possible_patterns = []
        for comb in itertools.permutations(keywords_with_types, r=len(keywords_with_types)):
            # Add the first empty pattern to this list of possible patterns
            possible_patterns_per_comb = []
            pattern = SupportedGraphPattern()
            possible_patterns_per_comb.append(pattern)

            for i in range(0, len(comb) - 1):
                kw1, t1 = comb[i]
                kw2, t2 = comb[i + 1]

                # Extend all previously found patterns
                possible_patterns_extended = []
                for pp in possible_patterns_per_comb:

                    # Find possible relations between these types and get the support
                    relation2support = self.graph.get_relations_between(t1, t2)
                    if ASSOCIATED not in relation2support:
                        relation2support[ASSOCIATED] = 0
                    for relation, support in relation2support.items():
                        pp_copy = pp.copy()
                        pp_copy.add_supported_fact_patterns(SupportedFactPattern(kw1, t1, relation, kw2, t2, support))
                        possible_patterns_extended.append(pp_copy)

                # old patterns are have now been extended
                possible_patterns_per_comb = copy.copy(possible_patterns_extended)

            # add all patterns for this combination only if the pattern has not been included yet
            # a flipped pattern (s, p, o) == (o, p, s) is not a new pattern because they will
            # result in the same visualization for the user. The query engine will order s, p, o based on r
            # automatically. So we don't need to generated flipped versions here
            # So for each new pattern check whether an existing pattern already contains the flipped version
            for new_candidate in possible_patterns_per_comb:
                match = False
                for existing_pattern in final_possible_patterns:
                    if new_candidate.is_flipped_equal_to_other(existing_pattern):
                        match = True
                        break
                if not match:
                    final_possible_patterns.append(new_candidate)

        # Now support the query patterns by their minimum support
        final_possible_patterns.sort(key=lambda x: x.minimum_support, reverse=True)
        return final_possible_patterns

    def translate_keywords_old(self, keyword_lists: List[str]) -> [SupportedGraphPattern]:
        # The first step is to transform keywords into entities
        # Then for each set of possible entities the most supported translation is searched
        # Most supported means to have the highest support (be detected in the most documents)
        # Force to be a list (must have the same order across the following script
        keyword_lists = list(keyword_lists)
        keywords_with_types = list()
        for keywords in keyword_lists:
            entities = self.translation.convert_text_to_entity(keywords)
            logging.debug(f'Found entities: {entities}')
            # What is a variable?
            if len(entities) == 1 and list(entities)[0].entity_type == ENTITY_TYPE_VARIABLE:
                # ID should be something like this f'?{var_type}({var_type})'
                var_type = VAR_TYPE.search(list(entities)[0].entity_id)
                if var_type:
                    ms_type = var_type.group(1)
                else:
                    # We have the type ALL ->
                    raise KeyError('The All-type for variables is not supported')
            else:
                # Get type from most supported entity
                ms_type = Keyword2GraphTranslation.greedy_find_most_supported_entity_type(entities)

            keywords_with_types.append((keywords, ms_type))

        logging.debug(f'Generating possible query patterns for: {keywords_with_types}')
        # Next find all possible query patterns
        patterns = self.find_all_possible_query_patterns(keywords_with_types)

        logging.debug(f'{len(patterns)} patterns have been generated.')
        # Compose the result
        results = []

        # Filter for specific patterns
        specific_patterns = list([p for p in patterns if p.is_specific()])
        # Add the most specific and highly supported pattern
        if len(specific_patterns) > 0:
            results.append(specific_patterns[0])
        if len(specific_patterns) > 1:
            # If there is an alternative add it
            results.append(specific_patterns[1])

        # Find the associated pattern
        associated_patterns = list([p for p in patterns if p.is_associated()])
        if len(associated_patterns) > 0:
            results.append(associated_patterns[0])

        return results

    def split_variables_and_entities(self, keyword_lists: List[str]) -> Tuple[List[str], List[str]]:
        """
        Identifies which keywords belong to entities or to variables
        :param keyword_lists: a list of keyword lists
        :return: keywords that belong to variables, keywords that belong to entities
        """
        keywords2variables, searched_entity_terms = dict(), []
        for keywords in keyword_lists:
            entities = self.translation.convert_text_to_entity(keywords)
            logging.debug(f'Found entities: {entities}')
            # What is a variable?
            if len(entities) == 1 and list(entities)[0].entity_type == ENTITY_TYPE_VARIABLE:
                # ID should be something like this f'?{var_type}({var_type})'
                var_type = VAR_TYPE.search(list(entities)[0].entity_id)
                if var_type:
                    ms_type = var_type.group(1)
                    ms_type = self.translation.variable_type_mappings[ms_type.lower()]
                    if ms_type == TARGET:
                        ms_type = GENE
                else:
                    # We have the type ALL ->
                    ms_type = "All"
                keywords2variables[keywords] = ms_type
            else:
                searched_entity_terms.append(keywords)

        return keywords2variables, searched_entity_terms

    def retrieve_latest_indexed_documents(self, collection2ids) -> List[IndexedDocument]:
        """
        Retrieve latest TOP_NEWEST_DOCUMENTS indexed documents
        :param collection2ids: a dict mapping collections to document ids
        :return: a list of indexed documents
        """
        collection2count = {k: len(v) for k, v in collection2ids.items()}
        logging.info(f'Compute patterns from following documents: {collection2count}')

        session = SessionExtended.get()
        no_of_documents = sum(collection2count.values())

        # if more than k documents are retrieved, we reduce the set of documents to the latest k ones
        if no_of_documents > PatternDiscovery.TOP_NEWEST_DOCUMENTS:
            # create query documents and get metadata
            doc_results = list()
            for collection, document_ids in collection2ids.items():
                doc_results.extend([QueryDocumentResult(document_id=doc_id, title="", authors="", journals="",
                                                        publication_year=0, publication_month=0, var2substitution={},
                                                        confidence=0.0, position2provenance_ids={},
                                                        document_collection=collection) for doc_id in document_ids])

            # apply filter
            doc_results = QueryEngine.enrich_document_results_with_metadata(doc_results, collection2ids)
            doc_results = self.date_ranker.rank_document(None, doc_results)
            doc_results = doc_results[:PatternDiscovery.TOP_NEWEST_DOCUMENTS]

            collection2ids = {k: set() for k, v in collection2ids.items()}
            for res in doc_results:
                collection2ids[res.document_collection].add(res.document_id)

        # now retrieve the actual document data
        indexed_documents = list()
        for collection, ids in collection2ids.items():
            indexed_documents.extend(retrieve_indexed_documents_from_database_small(session=session,
                                                                                    document_ids=ids,
                                                                                    document_collection=collection))
        return indexed_documents

    def translate_keywords(self, keyword_lists: List[str]) -> [SupportedGraphPattern]:
        """

        :param keyword_lists:
        :return:
        """

        # Step 1: divide keywords into entities and variables
        keywords2variables, searched_entity_terms = self.split_variables_and_entities(keyword_lists)

        # Step 2: discovery relevant documents that contain all searched entities
        collection2ids, keyword2entity_keys = self.discovery.retrieve_relevant_documents_for_concepts(
            searched_entity_terms,
            self.discovery.corpus.collections)

        # Step 3: retrieve the latest k indexed documents that contain all searched entities
        indexed_documents = self.retrieve_latest_indexed_documents(collection2ids)

        # Step 4: identify statements that contain one of the searched entities as subject/object
        # sort statements by their frequency
        statements = self.get_statements_ranked_by_frequency(indexed_documents, keyword2entity_keys)
        # Find all statements that do not have an associated relation

        statements_without_associations = [stmt for stmt in statements if stmt.relation != ASSOCIATED]
        specific_pattern1 = self.greedy_get_most_frequent_statements(statements_without_associations,
                                                                     keyword2entity_keys)
        pattern1_statements = [s[0] for s in specific_pattern1]

        # ignore already selected statements from pattern 1 as an alternative here
        statements_without_associations = [stmt for stmt in statements_without_associations
                                           if stmt not in pattern1_statements]
        specific_pattern2 = self.greedy_get_most_frequent_statements(statements_without_associations,
                                                                     keyword2entity_keys)

        statements_association_only = [stmt for stmt in statements if stmt.relation == ASSOCIATED]
        associated_pattern = self.greedy_get_most_frequent_statements(statements_association_only, keyword2entity_keys)

        result = []
        for pattern in [specific_pattern1, specific_pattern2, associated_pattern]:
            # skip empty patterns
            if len(pattern) == 0:
                continue

            self.enrich_pattern_with_variable(keywords2variables, pattern, indexed_documents)

            pattern_data = []
            for stmt, keyword1, keyword2 in pattern:
                pattern_data.append((keyword1, stmt.relation, keyword2))
            result.append(pattern_data)
        return result

    @staticmethod
    def greedy_get_most_frequent_statements(statements: List[StatementExtraction], keyword2entity_keys):
        selected_pattern = list()
        # statements are already sorted by their frequency
        selected_keywords = set()
        for statement in statements:
            for keyword1, entity_keys1 in keyword2entity_keys.items():
                for keyword2, entity_keys2 in keyword2entity_keys.items():
                    # only select one edge between two keywords
                    if (keyword1, keyword2) in selected_keywords:
                        continue

                    cond1 = get_unique_entity_key(statement.subject_type, statement.subject_id) in entity_keys1
                    cond2 = get_unique_entity_key(statement.object_type, statement.object_id) in entity_keys2

                    if cond1 and cond2:
                        selected_pattern.append((statement, keyword1, keyword2))
                        # ensure that direction does not matter
                        # and that we only select on edge per keyword pair
                        selected_keywords.add((keyword1, keyword2))
                        selected_keywords.add((keyword2, keyword1))

                        # we can stop as soon as we picked an edge between each pair of keywords
                        if len(selected_pattern) == len(keyword2entity_keys) - 1:
                            return selected_pattern

        # pattern does not include enough information (otherwise the inner return would have fired)
        # so we ignore that pattern and just return an empty one
        return []

    @staticmethod
    def get_statements_ranked_by_frequency(documents: List[IndexedDocument],
                                           keyword2entity_keys: Dict[str, Set[str]]) -> List[ScoredDocumentStatement]:
        # first identify all allowed entity keys
        allowed_entity_keys = set()
        for entity_keys in keyword2entity_keys.values():
            allowed_entity_keys.update(entity_keys)

        # next find statements that have one of the searched entities as subject or object
        statement2frequency = dict()
        key2statement = dict()
        for indexed_document in documents:
            for scored_statement in indexed_document.scored_statements:
                # only statements between searched entities are important
                # all other statements can be ignored
                if scored_statement.subject.get_unique_key() not in allowed_entity_keys:
                    continue
                if scored_statement.object.get_unique_key() not in allowed_entity_keys:
                    continue

                statement_key = scored_statement.get_unique_key()

                if statement_key not in statement2frequency:
                    statement2frequency[statement_key] = scored_statement.frequency
                    key2statement[statement_key] = scored_statement
                else:
                    statement2frequency[statement_key] += scored_statement.frequency

        # sort by highest frequency
        statements = sorted(statement2frequency.items(), key=lambda x: x[1], reverse=True)
        return [key2statement[key] for key, _ in statements]

    def enrich_pattern_with_variable(self, keywords2variables, pattern, documents: List[IndexedDocument]):
        so2relations = defaultdict(set)
        spo2support = defaultdict(int)
        for document in documents:
            for statement in document.scored_statements:
                so2relations[(statement.subject_type, statement.object_type)].add(statement.relation)
                spo2support[(statement.subject_type, statement.relation, statement.object_type)] += statement.frequency

        # add the most likely statement for each var type in our set of searched variable types
        for var_keywords, var_type in keywords2variables.items():
            candidates = []
            for statement, kw1, kw2 in pattern:
                for keywords, statement_type in [(kw1, statement.subject_type), (kw2, statement.object_type)]:
                    # use statement type as subject to connect variable to
                    for relation in so2relations[(statement_type, var_type)]:
                        candidates.append((statement_type, keywords, relation, var_type, var_keywords,
                                           spo2support[(statement_type, relation, var_type)]))

                    # use statement type as object to connect variable to
                    for relation in so2relations[(var_type, statement_type)]:
                        candidates.append((var_type, var_keywords, relation, statement_type, keywords,
                                           spo2support[(var_type, relation, statement_type)]))

            # sort by estimated support descending
            candidates.sort(key=lambda x: x[5], reverse=True)

            # add the most likely variable connection
            best_candidate = candidates[0]
            # pattern consists of triples ( statement, keywords1, keywords2)
            pattern.append((StatementExtraction(subject_id="", subject_type=best_candidate[0], subject_str="",
                                               predicate="", relation=best_candidate[2],
                                               object_id="", object_type=best_candidate[3], object_str="",
                                               sentence_id=0), best_candidate[1], best_candidate[4]))


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    g = Keyword2GraphTranslation()

    start = datetime.now()

    print(g.translate_keywords(["Diabetes", "Metformin"]))
    print("")
    print("")
    print("")
    print(g.translate_keywords(["Diabetes", "Metformin", "Patient"]))
    print("")
    print("")
    print("")
    print(g.translate_keywords(["Simvastatin", "Rhabdomyolysis"]))
    print("")
    print("")
    print("")
    print(g.translate_keywords(["Budesonide", "Nasal Administration", "Asthma"]))

    print('took: ', (datetime.now() - start).seconds, ' s')


if __name__ == "__main__":
    main()
