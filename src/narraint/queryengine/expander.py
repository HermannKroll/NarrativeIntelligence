import itertools
from typing import List

from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.query_hints import PREDICATE_EXPANSION, SYMMETRIC_PREDICATES, ENTITY_TYPE_EXPANSION


class QueryExpander:

    @staticmethod
    def expand_entity_types(entity_types: List[str]) -> List[str]:
        entity_types_ex = set([t for t in entity_types])
        for entity_type in entity_types:
            if entity_type in ENTITY_TYPE_EXPANSION:
                entity_types_ex.update(ENTITY_TYPE_EXPANSION[entity_type])
        return list(entity_types_ex)

    @staticmethod
    def expand_fact_pattern(fact_pattern: FactPattern) -> List[FactPattern]:
        predicate = fact_pattern.predicate
        if predicate in PREDICATE_EXPANSION or predicate in SYMMETRIC_PREDICATES:
            expansion = []
            if predicate in PREDICATE_EXPANSION:
                predicates = PREDICATE_EXPANSION[predicate]
                expansion = list([FactPattern(fact_pattern.subjects, p, fact_pattern.objects) for p in predicates])
            else:
                predicates = [predicate]

            if predicate in SYMMETRIC_PREDICATES:
                expansion.extend(
                    list([FactPattern(fact_pattern.objects, p, fact_pattern.subjects) for p in predicates]))

            return expansion
        else:
            return []

    @staticmethod
    def expand_query(graph_query: GraphQuery) -> List[GraphQuery]:
        """
        Expands the current query into a set of queries
        E.g. associated must be executed symmetric, interacts will be expanded to metabolises and interacts
        :param graph_query: a graph query object
        :return: a list of graph query. Each graph query consists of a set of alternatives for the original fact
        pattern
        """
        expanded_queries = []
        query_fact_patterns_expanded = []
        for idx, fp in enumerate(graph_query.fact_patterns):
            exp_cond1 = len(fp.subjects) > 1
            exp_cond2 = len(fp.objects) > 1
            exp_cond3 = fp.predicate in PREDICATE_EXPANSION or fp.predicate in SYMMETRIC_PREDICATES

            if exp_cond1 or exp_cond2 or exp_cond3:
                if fp.predicate in PREDICATE_EXPANSION:
                    predicates = PREDICATE_EXPANSION[fp.predicate]
                else:
                    predicates = [fp.predicate]

                expansion = []
                cross_product = list(
                    itertools.product(fp.subjects, predicates, fp.objects))
                expansion.extend(cross_product)

                if fp.predicate in SYMMETRIC_PREDICATES:
                    cross_product = list(
                        itertools.product(fp.objects, predicates, fp.subjects))
                    expansion.extend(cross_product)
                expanded_queries.append(GraphQuery([FactPattern([s], p, [o]) for s, p, o in expansion]))
                query_fact_patterns_expanded.append(expansion)

            else:
                expanded_queries.append(GraphQuery([FactPattern(fp.subjects, fp.predicate, fp.objects)]))
                query_fact_patterns_expanded.append([(list(fp.subjects)[0], fp.predicate, list(fp.objects)[0])])
        # copy already existing entities  + terms
        for q in expanded_queries:
            q.entity_sets = graph_query.entity_sets
            q.terms = graph_query.terms
        return expanded_queries
