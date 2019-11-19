import unittest

from stories.library_graph import LibraryGraph
from stories.story import GraphQuery
from stories.story import StoryProcessor


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
