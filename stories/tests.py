import unittest
from stories.library_graph import LibraryGraph
from stories.story import GraphQuery
from stories.story import StoryProcessor
from stories.graph import LabeledGraph


class QueryTests(unittest.TestCase):

    def setUp(self):
        self.lg1 = LibraryGraph()
        self.lg1.doc2facts = {'1': [('1', 'p', '2'), ('2', 'p', '3')], '2': [('1', 'q', '10')]}
        self.lg2 = LibraryGraph()
        self.lg2.doc2facts = {'1': [('1', 'p', '2'), ('2', 'p', '3')], '2': [('1', 'p', '10')]}
        self.lg3 = LibraryGraph()
        self.lg3.doc2facts = {'1': [('1', 'p', '2'), ('2', 'p', '3'), ('3', 'p', '1')]}

    def test_match_query_df1(self):
        query = GraphQuery()
        query.add_fact('1', 'p', '2')

        story = StoryProcessor(self.lg1)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 1)
        doc_id, var_subs = res[0]
        self.assertEqual(doc_id, '1')
        self.assertEqual(len(var_subs), 0)

    def test_no_match_query_1_df1(self):
        query = GraphQuery()
        query.add_fact('1', 'q', '2')

        story = StoryProcessor(self.lg1)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 0)

    def test_no_match_query_2_df1(self):
        query = GraphQuery()
        query.add_fact('1', 'not', '2')

        story = StoryProcessor(self.lg1)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 0)

    def test_2_var_in_query_df1(self):
        query = GraphQuery()
        query.add_fact('?x', 'p', '?y')
        query.add_fact('?y', 'p', '3')

        story = StoryProcessor(self.lg1)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 1)
        doc_id, var_subs = res[0]
        self.assertEqual(doc_id, '1')
        self.assertEqual('1' in var_subs['?x'], True)
        self.assertEqual(len(var_subs['?x']), 1)
        self.assertEqual('2' in var_subs['?y'], True)
        self.assertEqual(len(var_subs['?y']), 1)

    def test_no_match_2_var_in_query_df1(self):
        query = GraphQuery()
        query.add_fact('?x', 'p', '?y')
        query.add_fact('?y', 'q', '3')

        story = StoryProcessor(self.lg1)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 0)

    def test_3_var_in_query_df1(self):
        query = GraphQuery()
        query.add_fact('?x', 'p', '?y')
        query.add_fact('?y', 'p', '?z')

        story = StoryProcessor(self.lg1)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 1)
        doc_id, var_subs = res[0]
        self.assertEqual(doc_id, '1')
        self.assertEqual('1' in var_subs['?x'], True)
        self.assertEqual(len(var_subs['?x']), 1)
        self.assertEqual('2' in var_subs['?y'], True)
        self.assertEqual(len(var_subs['?y']), 1)
        self.assertEqual('3' in var_subs['?z'], True)
        self.assertEqual(len(var_subs['?z']), 1)

    def test_1_var_in_query_df2(self):
        query = GraphQuery()
        query.add_fact('1', 'p', '?y')

        story = StoryProcessor(self.lg2)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 2)
        doc_id, var_subs = res[0]
        self.assertEqual(doc_id, '1')
        self.assertEqual('2' in var_subs['?y'], True)
        self.assertEqual(len(var_subs['?y']), 1)

        doc_id, var_subs = res[1]
        self.assertEqual(doc_id, '2')
        self.assertEqual('10' in var_subs['?y'], True)
        self.assertEqual(len(var_subs['?y']), 1)

    def test_3_var_in_query_df3(self):
        query = GraphQuery()
        query.add_fact('?x', 'p', '?y')
        query.add_fact('?y', 'p', '?z')
        query.add_fact('?z', 'p', '?x')

        story = StoryProcessor(self.lg3)
        res = story.match_graph_query(query)

        self.assertEqual(len(res), 1)
        doc_id, var_subs = res[0]
        self.assertEqual(doc_id, '1')
        self.assertEqual('1' in var_subs['?x'], True)
        self.assertEqual('2' in var_subs['?x'], True)
        self.assertEqual('3' in var_subs['?x'], True)
        self.assertEqual(len(var_subs['?x']), 3)
        self.assertEqual('1' in var_subs['?y'], True)
        self.assertEqual('2' in var_subs['?y'], True)
        self.assertEqual('3' in var_subs['?y'], True)
        self.assertEqual(len(var_subs['?y']), 3)
        self.assertEqual('1' in var_subs['?z'], True)
        self.assertEqual('2' in var_subs['?z'], True)
        self.assertEqual('3' in var_subs['?z'], True)
        self.assertEqual(len(var_subs['?z']), 3)


class GraphTest(unittest.TestCase):
    def setUp(self):
        # a - p1 - b
        # d - p1 - b
        # b - p2 - c
        g1 = LabeledGraph()
        g1.add_edge('p1', 'a', 'b')
        g1.add_edge('p2', 'b', 'c')
        g1.add_edge('p1', 'd', 'b')
        self.g1 = g1

        # a - p1 - b
        g2 = LabeledGraph()
        g2.add_edge('p1', 'a', 'b')
        self.g2 = g2

        # a - p1 - b
        # d - p1 - b
        # b - p2 - c
        # c - p1 - f
        # c - p1 - e
        g3 = LabeledGraph()
        g3.add_edge('p1', 'a', 'b')
        g3.add_edge('p2', 'b', 'c')
        g3.add_edge('p1', 'd', 'b')
        g3.add_edge('p1', 'c', 'f')
        g3.add_edge('p1', 'c', 'e')
        self.g3 = g3

        # a - p1 - b
        # d - p1 - b
        # c - p1 - f
        # c - p1 - e
        g4 = LabeledGraph()
        g4.add_edge('p1', 'a', 'b')
        g4.add_edge('p1', 'd', 'b')
        g4.add_edge('p1', 'c', 'f')
        g4.add_edge('p1', 'c', 'e')
        self.g4 = g4

    def test_breath_search_g1_a(self):
        target = self.g1.breath_search(self.g1.get_node('a'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_search_g1_b(self):
        target = self.g1.breath_search(self.g1.get_node('b'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_search_g1_c(self):
        target = self.g1.breath_search(self.g1.get_node('c'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_search_g1_steps_1(self):
        target = self.g1.breath_search(self.g1.get_node('a'), max_steps=1)
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('d'))

    def test_breath_search_g1_steps_2(self):
        target = self.g1.breath_search(self.g1.get_node('a'), max_steps=2)
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_search_g4_a(self):
        target = self.g4.breath_search(self.g4.get_node('a'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('d'))
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('f'))
        self.assertIsNone(target.get_node('e'))

    def test_breath_search_g4_b(self):
        target = self.g4.breath_search(self.g4.get_node('b'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('d'))
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('f'))
        self.assertIsNone(target.get_node('e'))

    def test_breath_search_g4_c(self):
        target = self.g4.breath_search(self.g4.get_node('c'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('f'))
        self.assertIsNotNone(target.get_node('e'))
        self.assertIsNone(target.get_node('a'))
        self.assertIsNone(target.get_node('b'))
        self.assertIsNone(target.get_node('d'))

    def test_breath_search_g4_steps_1(self):
        target = self.g4.breath_search(self.g4.get_node('c'), max_steps=1)
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('f'))
        self.assertIsNotNone(target.get_node('e'))
        self.assertIsNone(target.get_node('a'))
        self.assertIsNone(target.get_node('b'))
        self.assertIsNone(target.get_node('d'))

    def test_breath_search_g4_steps_0(self):
        target = self.g4.breath_search(self.g4.get_node('c'), max_steps=0)
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('f'))
        self.assertIsNone(target.get_node('e'))
        self.assertIsNone(target.get_node('a'))
        self.assertIsNone(target.get_node('b'))
        self.assertIsNone(target.get_node('d'))

    def test_connectivity_components_g1(self):
        components = self.g1.compute_connectivity_components()

        self.assertEqual(1, len(components))
        target = components[0]
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))
        self.assertEqual(3, len(target))

    def test_connectivity_components_g4(self):
        components = self.g4.compute_connectivity_components()

        self.assertEqual(2, len(components))
        if components[0].get_node('a'):
            target0 = components[0]
            target1 = components[1]
        else:
            target0 = components[1]
            target1 = components[0]

        self.assertIsNotNone(target0.get_node('a'))
        self.assertIsNotNone(target0.get_node('b'))
        self.assertIsNotNone(target0.get_node('d'))
        self.assertIsNone(target0.get_node('c'))
        self.assertIsNone(target0.get_node('f'))
        self.assertIsNone(target0.get_node('e'))
        self.assertEqual(2, len(target0))

        self.assertIsNotNone(target1.get_node('c'))
        self.assertIsNotNone(target1.get_node('f'))
        self.assertIsNotNone(target1.get_node('e'))
        self.assertIsNone(target1.get_node('a'))
        self.assertIsNone(target1.get_node('b'))
        self.assertIsNone(target1.get_node('d'))
        self.assertEqual(2, len(target1))
