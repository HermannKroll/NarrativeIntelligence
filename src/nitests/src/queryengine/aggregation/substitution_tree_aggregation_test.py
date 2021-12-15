from unittest import TestCase

from narraint.queryengine.aggregation.substitution_tree import ResultTreeAggregationBySubstitution
from narraint.queryengine.result import QueryDocumentResult, QueryEntitySubstitution


class SubstitutionTreeAggregationTest(TestCase):

    def test_aggregate_simple(self):
        entity_sub_a = QueryEntitySubstitution("a", "a", "a", entity_name="a")
        entity_sub_b = QueryEntitySubstitution("b", "b", "b", entity_name="b")

        result1 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, {"X": entity_sub_a}, 1.0, {})
        result2 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, {"X": entity_sub_a}, 1.0, {})
        result3 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, {"X": entity_sub_b}, 1.0, {})
        results = [result1, result2, result3]

        tree_aggregation = ResultTreeAggregationBySubstitution()
        ranked, _ = tree_aggregation.rank_results(results, ordered_var_names=["X"], freq_sort_desc=True, year_sort_desc=True)

        self.assertEqual(2, len(ranked.results))
        self.assertEqual(2, len(ranked.results[0].results))
        self.assertEqual({"X": entity_sub_a}, ranked.results[0].var2substitution)
        self.assertEqual(1, len(ranked.results[1].results))
        self.assertEqual({"X": entity_sub_b}, ranked.results[1].var2substitution)

