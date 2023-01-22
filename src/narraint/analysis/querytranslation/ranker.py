from narraint.analysis.querytranslation.data_graph import Query, DataGraph

import functools

from narraint.analysis.querytranslation.schema_graph import SchemaGraph


class QueryRanker:
    NAME = None

    def __init__(self):
        pass

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        pass

    @staticmethod
    def rank_queries_with_data_graph(queries: [Query], data_graph: DataGraph) -> [Query]:
        return QueryRanker.rank_queries(queries)


class TermBasedRanker:
    NAME = "TermBasedRanker"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # ignore all queries that have entities or statements
            if len(q.entities) > 0 or len(q.statements) > 0:
                continue

            # otherwise add the query
            relevant_queries.add(q)

        return sorted(relevant_queries, key=lambda x: len(x.terms), reverse=True)


class EntityBasedRanker:
    NAME = "EntityBasedRanker"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # ignore all queries that have statements
            if len(q.statements) > 0:
                continue

            # otherwise add the query
            relevant_queries.add(q)

        return sorted(relevant_queries, key=lambda x: len(x.entities), reverse=True)


class EntityFrequencyBasedRanker:
    NAME = "EntityFrequencyBasedRanker"

    @staticmethod
    def compare_queries(q1: Query, q2: Query):
        if len(q1.entities) > len(q2.entities):
            return 1
        elif len(q1.entities) < len(q2.entities):
            return -1
        elif len(q1.entities) == len(q2.entities):
            if q1.entity_support > q2.entity_support:
                return 1
            elif q1.entity_support < q2.entity_support:
                return -1
            else:
                return 0
        else:
            if len(q1.terms) > len(q2.terms):
                return 1
            elif len(q1.terms) < len(q2.terms):
                return -1
            return 0

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # ignore all queries that have statements or no entities
            if len(q.statements) > 0:
                continue

            # otherwise add the query
            relevant_queries.add(q)

        return sorted(relevant_queries, key=functools.cmp_to_key(EntityFrequencyBasedRanker.compare_queries),
                      reverse=True)


class StatementBasedRanker:
    NAME = "StatementBasedRanker"

    @staticmethod
    def compare_queries(q1: Query, q2: Query):
        if len(q1.relations) > len(q2.relations):
            return 1
        elif len(q1.relations) < len(q2.relations):
            return -1

        if len(q1.statements) > len(q2.statements):
            return 1
        elif len(q1.statements) < len(q2.statements):
            return -1

        return 0

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # ignore all queries that do not have statements
            if len(q.statements) == 0:
                continue

            # otherwise add the query
            relevant_queries.add(q)

        return sorted(relevant_queries, key=functools.cmp_to_key(StatementBasedRanker.compare_queries), reverse=True)


class StatementFrequencyBasedRanker:
    NAME = "StatementFrequencyBasedRanker"

    @staticmethod
    def compare_queries(q1: Query, q2: Query):
        if len(q1.relations) > len(q2.relations):
            return 1
        elif len(q1.relations) < len(q2.relations):
            return -1

        if len(q1.statements) > len(q2.statements):
            return 1
        elif len(q1.statements) < len(q2.statements):
            return -1
        else:
            if q1.statement_support > q2.statement_support:
                return 1
            elif q1.statement_support < q2.statement_support:
                return -1
            return 0

        return 0

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # ignore all queries that do not have statements
            if len(q.statements) == 0:
                continue

            # otherwise add the query
            relevant_queries.add(q)

        return sorted(relevant_queries, key=functools.cmp_to_key(StatementFrequencyBasedRanker.compare_queries),
                      reverse=True)


schema_graph = SchemaGraph()
RELATION_RELEVANCE_SCORE = {r: 0 for r in schema_graph.relations}
RELATION_RELEVANCE_SCORE["associated"] = -1


class MostSpecificQueryFirstRanker:
    NAME = "MostSpecificQueryFirstRanker"

    @staticmethod
    def compare_queries(q1: Query, q2: Query):
        if len(q1.relations) > len(q2.relations):
            return 1
        elif len(q1.relations) < len(q2.relations):
            return -1

        if len(q1.statements) > len(q2.statements):
            return 1
        elif len(q1.statements) < len(q2.statements):
            return -1
        else:
            # Length are equal
            if len(q1.statements.intersection(q2.statements)) == len(q1.statements):
                # they have the same statements
                # Prefer query with more entities
                if len(q1.entities) > len(q2.entities):
                    return 1
                elif len(q1.entities) < len(q2.entities):
                    return -1
                else:
                    # Entities set are equally long
                    # Prefer queries with more terms
                    return len(q1.terms) > len(q2.terms)
            else:
                # Equal number of statements but different statements
                # Prefer more specific relations (e.g. treats over associated)
                q1_so_relations = {(s, o): p for s, p, o in q1.statements}
                q2_so_relations = {(s, o): p for s, p, o in q2.statements}

                for (s, o) in q1_so_relations:
                    if (s, o) in q2_so_relations:
                        score1 = RELATION_RELEVANCE_SCORE[q1_so_relations[(s, o)]]
                        score2 = RELATION_RELEVANCE_SCORE[q2_so_relations[(s, o)]]
                        if score1 > score2:
                            return 1
                        elif score1 < score2:
                            return -1
                        else:
                            # scores are equal
                            continue

                # they are equally relevant
                if q1.statement_support > q2.statement_support:
                    return 1
                elif q1.statement_support < q2.statement_support:
                    return -1
                return 0

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        return sorted(queries, key=functools.cmp_to_key(MostSpecificQueryFirstRanker.compare_queries), reverse=True)


class MostSpecificQueryFirstLimit1Ranker:
    NAME = "MostSpecificQueryFirstLimit1Ranker"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = {q for q in queries if len(q.statements) == 1}
        return sorted(relevant_queries, key=functools.cmp_to_key(MostSpecificQueryFirstRanker.compare_queries),
                      reverse=True)


class MostSpecificQueryFirstLimit2Ranker:
    NAME = "MostSpecificQueryFirstLimit2Ranker"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = {q for q in queries if 0 < len(q.statements) <= 2}
        return sorted(relevant_queries, key=functools.cmp_to_key(MostSpecificQueryFirstRanker.compare_queries),
                      reverse=True)


class TreatsRanker:
    NAME = "TreatsRanker"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            if len(q.statements) == 1 and 'treats' in {r for _, r, _ in q.statements} and len(q.entities) == 2:
                relevant_queries.add(q)
        return sorted(relevant_queries, key=functools.cmp_to_key(MostSpecificQueryFirstRanker.compare_queries),
                      reverse=True)


class AssociatedRanker:
    NAME = "AssociatedRanker"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        relevant_queries = set()
        for q in queries:
            if len(q.statements) == 1 and 'associated' in {r for _, r, _ in q.statements} and len(q.entities) == 2:
                relevant_queries.add(q)
        return sorted(relevant_queries, key=lambda x: x.get_minimum_support(), reverse=True)


class MostSupportedQuery:
    NAME = "MostSupportedQuery"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        return NotImplemented

    @staticmethod
    def rank_queries_with_data_graph(queries: [Query], data_graph: DataGraph) -> [Query]:
        relevant_queries = set()
        for q in queries:
            supp = len(data_graph.compute_query(q))
            if supp > 0:
                relevant_queries.add(q)
        return sorted(relevant_queries, key=lambda x: len(data_graph.compute_query(x)), reverse=True)


class MostSpecificQueryWithResults:
    NAME = "MostSpecificQueryWithResults"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        return NotImplemented

    @staticmethod
    def rank_queries_with_data_graph(queries: [Query], data_graph: DataGraph) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # if len(q.statements) == 1 and 'associated' in {r for _, r, _ in q.statements} and len(q.entities) == 2:
            if len(q.statements) >= 1 and 'associated' not in {r for _, r, _ in q.statements} and len(
                    data_graph.compute_query(q)) > 0:
                relevant_queries.add(q)
        return sorted(relevant_queries, key=lambda x: len(data_graph.compute_query(x)), reverse=True)


class AssociatedRankerWithQueryResults:
    NAME = "AssociatedRankerWithQueryResults"

    @staticmethod
    def rank_queries(queries: [Query]) -> [Query]:
        return NotImplemented

    @staticmethod
    def rank_queries_with_data_graph(queries: [Query], data_graph: DataGraph) -> [Query]:
        relevant_queries = set()
        for q in queries:
            # if len(q.statements) == 1 and 'associated' in {r for _, r, _ in q.statements} and len(q.entities) == 2:
            if 'associated' in {r for _, r, _ in q.statements} and len(data_graph.compute_query(q)) > 0:
                relevant_queries.add(q)
        return sorted(relevant_queries, key=lambda x: len(data_graph.compute_query(x)), reverse=True)
