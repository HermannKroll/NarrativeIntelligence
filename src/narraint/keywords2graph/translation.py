import argparse
import copy
import itertools
import logging
from datetime import datetime
from typing import List

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.keywords2graph.schema_support_graph import SchemaSupportGraph
from narraint.queryengine.query_hints import PREDICATE_ASSOCIATED, ENTITY_TYPE_VARIABLE, VAR_TYPE
from narrant.entity.entity import Entity

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

    @staticmethod
    def greedy_find_most_supported_entity_type(entities: [Entity]):
        entity_ids = {e.entity_id for e in entities}
        entity_types = {e.entity_type for e in entities}

        session = SessionExtended.get()
        query = session.query(TagInvertedIndex.entity_id, TagInvertedIndex.entity_type, TagInvertedIndex.support)
        query = query.filter(TagInvertedIndex.entity_id.in_(entity_ids))
        query = query.filter(TagInvertedIndex.entity_type.in_(entity_types))

        entity2support = {}
        for row in query:
            if (row.entity_type, row.entity_id) not in entity2support:
                entity2support[(row.entity_type, row.entity_id)] = 0

            entity2support[(row.entity_type, row.entity_id)] += row.support

        # Compute a sorted list
        entity_support_list = [(et, e, supp) for (et, e), supp in entity2support.items()]
        entity_support_list.sort(key=lambda x: x[2], reverse=True)

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

    def translate_keywords(self, keyword_lists: List[str]) -> [SupportedGraphPattern]:
        # The first step is to transform keywords into entities
        # Then for each set of possible entities the most supported translation is searched
        # Most supported means to have the highest support (be detected in the most documents)
        # Force to be a list (must have the same order scross the following script
        keyword_lists = list(keyword_lists)
        keywords_with_types = list()
        for keywords in keyword_lists:
            entities = self.translation.convert_text_to_entity(keywords)

            # Was is a variable?
            if len(entities) == 1 and list(entities)[0].entity_type == ENTITY_TYPE_VARIABLE:
                # ID should be something like this f'?{var_type}({var_type})'
                var_type = VAR_TYPE.search(list(entities)[0].entity_id)
                if var_type:
                    ms_type = var_type.group(1)
                else:
                    # We have the type ALL ->
                    ms_type = "All"
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


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

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

    print('took: ', (datetime.now() - start).seconds, ' s')


if __name__ == "__main__":
    main()
