import argparse
import ast
import copy
import itertools
import logging
from datetime import datetime
from typing import List

from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.keywords2graph.schema_support_graph import SchemaSupportGraph
from narraint.queryengine.query import GraphQuery
from narrant.entity.entity import Entity


class SupportedFactPattern:

    def __init__(self, keyword1, entity_type1, relation, keyword2, entity_type2, support):
        self.keyword1 = keyword1
        self.entity_type1 = entity_type1
        self.relation = relation
        self.keyword2 = keyword2
        self.entity_type2 = entity_type2
        self.support = support


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
        return 'associated' not in self.get_relations()

    def is_associated(self):
        relations = self.get_relations()
        return len(relations) == 1 and 'associated' in relations

    def to_json_data(self):
        data = []
        for fp in self.fact_patterns:
            data.append((fp.keyword1, fp.relation, fp.keyword2))
        return data


class Keyword2GraphTranslation:

    def __init__(self):
        self.graph: SchemaSupportGraph = SchemaSupportGraph.instance()
        self.tagger: EntityTagger = EntityTagger.instance()

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
                    for relation, support in relation2support.items():
                        pp_copy = pp.copy()
                        pp_copy.add_supported_fact_patterns(SupportedFactPattern(kw1, t1, relation, kw2, t2, support))
                        possible_patterns_extended.append(pp_copy)

                # old patterns are have now been extended
                possible_patterns_per_comb = copy.copy(possible_patterns_extended)

            # add all patterns for this combination
            final_possible_patterns.extend(possible_patterns_per_comb)

        # Now support the query patterns by their minimum support
        final_possible_patterns.sort(key=lambda x: x.minimum_support, reverse=True)
        return final_possible_patterns

    def translate_keywords(self, keyword_lists: List[str]) -> [GraphQuery]:
        # The first step is to transform keywords into entities
        # Then for each set of possible entities the most supported translation is searched
        # Most supported means to have the highest support (be detected in the most documents)
        # Force to be a list (must have the same order scross the following script
        keyword_lists = list(keyword_lists)
        keywords_with_types = list()
        for keywords in keyword_lists:
            entities = self.tagger.tag_entity(keywords)
            ms_type = Keyword2GraphTranslation.greedy_find_most_supported_entity_type(entities)

            keywords_with_types.append((keywords, ms_type))

        # Next find all possible query patterns
        patterns = self.find_all_possible_query_patterns(keywords_with_types)

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
        results.append(associated_patterns[0])

        return [r.to_json_data() for r in results]


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
