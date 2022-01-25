import random
from collections import defaultdict
from unittest import TestCase

from narraint.queryengine.aggregation.substitution_tree import ResultTreeAggregationBySubstitution
from narraint.queryengine.result import QueryDocumentResult, QueryEntitySubstitution, QueryResultAggregate, \
    QueryResultAggregateList


class SubstitutionTreeAggregationTest(TestCase):

    def count_substitutions(self, ranked_results, ordered_var_names):
        substitution_count = defaultdict(int)
        todo = [(ranked_results.results, {}, 0)]
        while todo:
            current_results, level_sub, level = todo.pop()
            for current in current_results:
                if isinstance(current, QueryResultAggregateList):
                    todo.append((current.results, level_sub, level))
                elif isinstance(current, QueryResultAggregate):
                    level_sub_copy = level_sub.copy()
                    level_sub_copy[ordered_var_names[level]] = current.var2substitution[ordered_var_names[level]]
                    todo.append((current.results, level_sub_copy, level + 1))
                elif isinstance(current, QueryDocumentResult):
                    if current.var2substitution != level_sub:
                        print('a')
                    # it is a final substitution
                    key = []
                    for var in ordered_var_names:
                        key.append(var)
                        key.append(level_sub[var].entity_id)
                    key = tuple(key)
                    substitution_count[key] += 1
                else:
                    raise ValueError('Not expected element in document tree')
        return substitution_count

    def test_aggregate_simple(self):
        entity_sub_a = QueryEntitySubstitution("a", "a", "a", entity_name="a")
        entity_sub_b = QueryEntitySubstitution("b", "b", "b", entity_name="b")

        result1 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, {"X": entity_sub_a}, 1.0, {})
        result2 = QueryDocumentResult(2, "Test", "Kroll", "Fake", 2000, 0, {"X": entity_sub_a}, 1.0, {})
        result3 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, {"X": entity_sub_b}, 1.0, {})
        results = [result1, result2, result3]
        o_vars = ["X"]
        tree_aggregation = ResultTreeAggregationBySubstitution()
        ranked, _ = tree_aggregation.rank_results(results, ordered_var_names=o_vars, freq_sort_desc=True,
                                                  year_sort_desc=True)

        s_count = self.count_substitutions(ranked, o_vars)
        self.assertEqual(2, s_count[('X', 'a')])
        self.assertEqual(1, s_count[('X', 'b')])

        self.assertEqual(2, len(ranked.results))
        self.assertEqual(2, len(ranked.results[0].results))
        self.assertEqual({"X": entity_sub_a}, ranked.results[0].var2substitution)
        self.assertEqual(1, len(ranked.results[1].results))
        self.assertEqual({"X": entity_sub_b}, ranked.results[1].var2substitution)

    def test_aggregate_two_levels(self):
        # X: a (2) -> (Y: a (2), Y: b (1))
        # X: b (1) -> (Y: b (1))
        entity_sub_a = QueryEntitySubstitution("a", "a", "a", entity_name="a")
        entity_sub_b = QueryEntitySubstitution("b", "b", "b", entity_name="b")
        var_sub_1 = {"X": entity_sub_a, "Y": entity_sub_a}
        var_sub_2 = {"X": entity_sub_a, "Y": entity_sub_b}
        var_sub_3 = {"X": entity_sub_b, "Y": entity_sub_b}

        result1 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, var_sub_1, 1.0, {})
        result2 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, var_sub_2, 1.0, {})
        result3 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, var_sub_3, 1.0, {})
        results = [result1, result1, result2, result3]
        o_vars = ["X", "Y"]
        tree_aggregation = ResultTreeAggregationBySubstitution()
        ranked, _ = tree_aggregation.rank_results(results, ordered_var_names=o_vars, freq_sort_desc=True,
                                                  year_sort_desc=True)

        s_count = self.count_substitutions(ranked, o_vars)
        self.assertEqual(2, s_count[('X', 'a', 'Y', 'a')])
        self.assertEqual(1, s_count[('X', 'a', 'Y', 'b')])
        self.assertEqual(1, s_count[('X', 'b', 'Y', 'b')])

        # 2 subs on level 1
        self.assertEqual(2, len(ranked.results))
        # 2 subs on level 2 of first sub
        self.assertEqual(1, len(ranked.results[0].results))
        self.assertEqual(2, len(ranked.results[0].results[0].results))
        self.assertEqual(var_sub_1, ranked.results[0].results[0].results[0].results[0].var2substitution)
        # 1 sub on level 1 of second sub
        self.assertEqual(1, len(ranked.results[1].results))
        self.assertEqual(var_sub_2, ranked.results[0].results[0].results[1].results[0].var2substitution)

    def test_aggregate_two_levels_complicated(self):
        # X: a -> (Y: a (4), Y: b (1))
        # X: b -> (Y: b (3))
        entity_sub_a = QueryEntitySubstitution("a", "a", "a", entity_name="a")
        entity_sub_b = QueryEntitySubstitution("b", "b", "b", entity_name="b")
        var_sub_1 = {"X": entity_sub_a, "Y": entity_sub_a}
        var_sub_2 = {"X": entity_sub_a, "Y": entity_sub_b}
        var_sub_3 = {"X": entity_sub_b, "Y": entity_sub_b}

        result1 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, var_sub_1, 1.0, {})
        result2 = QueryDocumentResult(2, "Test", "Kroll", "Fake", 2000, 0, var_sub_2, 1.0, {})
        result3 = QueryDocumentResult(3, "Test", "Kroll", "Fake", 2000, 0, var_sub_3, 1.0, {})
        results = [result1, result1, result2, result3, result3, result3, result1, result1]
        o_vars = ["X", "Y"]
        tree_aggregation = ResultTreeAggregationBySubstitution()
        ranked, _ = tree_aggregation.rank_results(results, ordered_var_names=o_vars, freq_sort_desc=True,
                                                  year_sort_desc=True)

        s_count = self.count_substitutions(ranked, o_vars)
        self.assertEqual(4, s_count[('X', 'a', 'Y', 'a')])
        self.assertEqual(1, s_count[('X', 'a', 'Y', 'b')])
        self.assertEqual(3, s_count[('X', 'b', 'Y', 'b')])

    def test_aggregate_three_levels_complicated(self):
        # X: a -> Y: a -> Z: a (4) | X: a -> Y: a -> Z: b (1)
        # X: b -> (Y: b (3))
        entity_sub_a = QueryEntitySubstitution("a", "a", "a", entity_name="a")
        entity_sub_b = QueryEntitySubstitution("b", "b", "b", entity_name="b")
        var_sub_1 = {"X": entity_sub_a, "Y": entity_sub_a, "Z": entity_sub_a}
        var_sub_2 = {"X": entity_sub_a, "Y": entity_sub_b, "Z": entity_sub_a}
        var_sub_3 = {"X": entity_sub_b, "Y": entity_sub_b, "Z": entity_sub_a}

        result1 = QueryDocumentResult(1, "Test", "Kroll", "Fake", 2000, 0, var_sub_1, 1.0, {})
        result2 = QueryDocumentResult(2, "Test", "Kroll", "Fake", 2000, 0, var_sub_2, 1.0, {})
        result3 = QueryDocumentResult(3, "Test", "Kroll", "Fake", 2000, 0, var_sub_3, 1.0, {})
        results = [result1, result1, result2, result3, result3, result3, result1, result1]
        o_vars = ["X", "Y", "Z"]
        tree_aggregation = ResultTreeAggregationBySubstitution()
        ranked, _ = tree_aggregation.rank_results(results, ordered_var_names=o_vars, freq_sort_desc=True,
                                                  year_sort_desc=True)

        s_count = self.count_substitutions(ranked, o_vars)
        self.assertEqual(4, s_count[('X', 'a', 'Y', 'a', "Z", "a")])
        self.assertEqual(1, s_count[('X', 'a', 'Y', 'b', "Z", "a")])
        self.assertEqual(3, s_count[('X', 'b', 'Y', 'b', "Z", "a")])

    def test_auto_generated_two_levels(self):
        samples = 10000
        alphabet = ["a", "b", "c", "d", "e", "f"]
        o_vars = ["X", "Y"]
        entity_subs_x = list([QueryEntitySubstitution(l, l, l) for l in alphabet])
        entity_subs_y = list([QueryEntitySubstitution(l, l, l) for l in alphabet])

        sub_plan = defaultdict(int)
        documents = []
        for i in range(0, samples):
            x_sub = random.choice(entity_subs_x)
            y_sub = random.choice(entity_subs_y)
            var2sub = {"X": x_sub, "Y": y_sub}

            documents.append(QueryDocumentResult(i, "Test", "", "", 2000, 0, var2sub, 1.0, {}))
            key = ("X", x_sub.entity_id, "Y", y_sub.entity_id)
            sub_plan[key] += 1

        tree_aggregation = ResultTreeAggregationBySubstitution()
        ranked, _ = tree_aggregation.rank_results(documents, ordered_var_names=o_vars, freq_sort_desc=True,
                                                  year_sort_desc=True)

        s_count = self.count_substitutions(ranked, o_vars)
        self.assertEqual(sub_plan, s_count)
