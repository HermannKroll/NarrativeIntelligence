import logging
from collections import defaultdict
from datetime import datetime
from typing import List, Set, Tuple, Dict

from kgextractiontoolbox.document.narrative_document import StatementExtraction
from narraint.backend.database import SessionExtended
from narraint.entity.query_translation import QueryTranslation
from narraint.keywords2graph.schema_support_graph import SchemaSupportGraph
from narraint.pattern_discovery.discovery import PatternDiscovery
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.query_hints import PREDICATE_ASSOCIATED, ENTITY_TYPE_VARIABLE, VAR_TYPE
from narraint.queryengine.result import QueryDocumentResult
from narraint.ranking.indexed_document import retrieve_indexed_documents_from_database_small, IndexedDocument, \
    ScoredDocumentStatement
from narraint.ranking.ranking import PublicationDateRank
from narrant.entity.entity import get_unique_entity_key
from narrant.entitylinking.enttypes import TARGET, GENE

ASSOCIATED = PREDICATE_ASSOCIATED


class VariableTypeNotSupportedError(Exception):
    pass


class TwoEntitiesRequiredError(Exception):
    pass


class NoDocumentsFoundError(Exception):
    pass


class GeneratedStatement:

    def __init__(self, statement: StatementExtraction, keyword1: str, keyword2: str):
        self.statement = statement
        self.keyword1 = keyword1
        self.keyword2 = keyword2

class GeneratedPattern:

    def __init__(self):
        self.selected_statements = list()

    def add_generated_statement(self, statement: GeneratedStatement):
        self.selected_statements.append(statement)

    def to_json_data(self):
        pattern_data = []
        for stmt in self.selected_statements:
            pattern_data.append((stmt.keyword1, stmt.statement.relation, stmt.keyword2))
        return pattern_data


class Keyword2GraphTranslation:

    def __init__(self):
        self.graph: SchemaSupportGraph = SchemaSupportGraph()
        self.translation: QueryTranslation = QueryTranslation()
        self.discovery: PatternDiscovery = PatternDiscovery()
        self.date_ranker = PublicationDateRank()

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
                    try:
                        ms_type = self.translation.variable_type_mappings[ms_type.lower()]
                        if ms_type == TARGET:
                            ms_type = GENE
                        keywords2variables[keywords] = ms_type
                    except KeyError:
                        raise VariableTypeNotSupportedError()
                else:
                    raise VariableTypeNotSupportedError()

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

    def translate_keywords(self, keyword_lists: List[str]):
        """

        :param keyword_lists:
        :return:
        """

        # Step 1: divide keywords into entities and variables
        keywords2variables, searched_entity_terms = self.split_variables_and_entities(keyword_lists)

        if len(searched_entity_terms) < 2:
            raise TwoEntitiesRequiredError(f'At least two entities are required. Given: {searched_entity_terms}')

        # Step 2: discovery relevant documents that contain all searched entities
        collection2ids, keyword2entity_keys = self.discovery.retrieve_relevant_documents_for_concepts(
            searched_entity_terms,
            self.discovery.corpus.collections)

        # Step 3: retrieve the latest k indexed documents that contain all searched entities
        indexed_documents = self.retrieve_latest_indexed_documents(collection2ids)

        # we might not have any documents
        if len(indexed_documents) == 0:
            raise NoDocumentsFoundError(f"Entities {searched_entity_terms} do not co-occurr together")

        # Step 4: identify statements that contain one of the searched entities as subject/object
        # sort statements by their frequency
        statements = self.get_statements_ranked_by_frequency(indexed_documents, keyword2entity_keys)
        # Find all statements that do not have an associated relation

        statements_without_associations = [stmt for stmt in statements if stmt.relation != ASSOCIATED]
        specific_pattern1 = self.greedy_get_most_frequent_statements(statements_without_associations,
                                                                     keyword2entity_keys)
        pattern1_statements = [s.statement for s in specific_pattern1.selected_statements]

        # ignore already selected statements from pattern 1 as an alternative here
        statements_without_associations = [stmt for stmt in statements_without_associations
                                           if stmt not in pattern1_statements]
        specific_pattern2 = self.greedy_get_most_frequent_statements(statements_without_associations,
                                                                     keyword2entity_keys)

        statements_association_only = [stmt for stmt in statements if stmt.relation == ASSOCIATED]
        associated_pattern = self.greedy_get_most_frequent_statements(statements_association_only, keyword2entity_keys)

        generated_patterns = []
        for pattern in [specific_pattern1, specific_pattern2, associated_pattern]:
            # skip empty patterns
            if len(pattern.selected_statements) == 0:
                continue

            self.enrich_pattern_with_variables(keywords2variables, pattern, indexed_documents)
            generated_patterns.append(pattern)
        return generated_patterns

    @staticmethod
    def greedy_get_most_frequent_statements(statements: List[StatementExtraction], keyword2entity_keys) \
            -> GeneratedPattern:
        """
        Selects the most supported statements first
        :param statements: a list of statement extractions
        :param keyword2entity_keys: dict mapping keywords to allowed entity keys
        :return: a list (statement, keyword1, keyword2)
        """
        selected_pattern = GeneratedPattern()
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
                        selected_pattern.add_generated_statement(GeneratedStatement(statement, keyword1, keyword2))
                        # ensure that direction does not matter
                        # and that we only select on edge per keyword pair
                        selected_keywords.add((keyword1, keyword2))
                        selected_keywords.add((keyword2, keyword1))

                        # we can stop as soon as we picked an edge between each pair of keywords
                        if len(selected_pattern.selected_statements) == len(keyword2entity_keys) - 1:
                            return selected_pattern

        # pattern does not include enough information (otherwise the inner return would have fired)
        # so we ignore that pattern and just return an empty one
        return None

    @staticmethod
    def get_statements_ranked_by_frequency(documents: List[IndexedDocument],
                                           keyword2entity_keys: Dict[str, Set[str]]) -> List[ScoredDocumentStatement]:
        """
        Generates a list of all known statements between the set of allowed entity keys. Sorts statements
        descending by their frequency
        :param documents: a list of indexed documents
        :param keyword2entity_keys: a set of allowed entity keys
        :return: a sorted list of statements (sort by frequency descending)
        """
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

    @staticmethod
    def enrich_pattern_with_variables(keywords2variables, pattern: GeneratedPattern, documents: List[IndexedDocument]):
        """
        Enriches a pattern by attaching the variables to the most likely connecting node, i.e., by adding a new
        statement that connects an existing node with the variable and yielding the most documents
        :param keywords2variables: dict mapping keywords to variable types
        :param pattern: the pattern to enrich
        :param documents: a list of indexed documents
        :return: None
        """
        # First retrieve information from the set of retrieved documents
        # We want to know the most supported connections between entity types
        so2relations = defaultdict(set)
        spo2support = defaultdict(int)
        for document in documents:
            for statement in document.scored_statements:
                so2relations[(statement.subject_type, statement.object_type)].add(statement.relation)
                spo2support[(statement.subject_type, statement.relation, statement.object_type)] += statement.frequency

        # add the most likely statement for each var type in our set of searched variable types
        for var_keywords, var_type in keywords2variables.items():
            candidates = []
            for stmt_data in pattern.selected_statements:
                statement, kw1, kw2 = stmt_data.statement, stmt_data.keyword1, stmt_data.keyword2
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
            # add candidate to pattern
            pattern.add_generated_statement(GeneratedStatement(StatementExtraction(
                subject_id="", subject_type=best_candidate[0], subject_str="",
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
