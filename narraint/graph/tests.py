import tempfile
import unittest

from narraint.config import GRAPH_GV
from narraint.graph.labeled import LabeledGraph


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

    def test_breath_first_search_g1_a(self):
        target = self.g1.breath_first_search(self.g1.get_node('a'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_first_search_g1_b(self):
        target = self.g1.breath_first_search(self.g1.get_node('b'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_first_search_g1_c(self):
        target = self.g1.breath_first_search(self.g1.get_node('c'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_first_search_g1_steps_1(self):
        target = self.g1.breath_first_search(self.g1.get_node('a'), max_steps=1)
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('d'))

    def test_breath_first_search_g1_steps_2(self):
        target = self.g1.breath_first_search(self.g1.get_node('a'), max_steps=2)
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('d'))

    def test_breath_first_search_g4_a(self):
        target = self.g4.breath_first_search(self.g4.get_node('a'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('d'))
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('f'))
        self.assertIsNone(target.get_node('e'))

    def test_breath_first_search_g4_b(self):
        target = self.g4.breath_first_search(self.g4.get_node('b'))
        self.assertIsNotNone(target.get_node('a'))
        self.assertIsNotNone(target.get_node('b'))
        self.assertIsNotNone(target.get_node('d'))
        self.assertIsNone(target.get_node('c'))
        self.assertIsNone(target.get_node('f'))
        self.assertIsNone(target.get_node('e'))

    def test_breath_first_search_g4_c(self):
        target = self.g4.breath_first_search(self.g4.get_node('c'))
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('f'))
        self.assertIsNotNone(target.get_node('e'))
        self.assertIsNone(target.get_node('a'))
        self.assertIsNone(target.get_node('b'))
        self.assertIsNone(target.get_node('d'))

    def test_breath_first_search_g4_steps_1(self):
        target = self.g4.breath_first_search(self.g4.get_node('c'), max_steps=1)
        self.assertIsNotNone(target.get_node('c'))
        self.assertIsNotNone(target.get_node('f'))
        self.assertIsNotNone(target.get_node('e'))
        self.assertIsNone(target.get_node('a'))
        self.assertIsNone(target.get_node('b'))
        self.assertIsNone(target.get_node('d'))

    def test_breath_first_search_g4_steps_0(self):
        target = self.g4.breath_first_search(self.g4.get_node('c'), max_steps=0)
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

    def test_save_to_dot(self):
        g1 = LabeledGraph()
        g1.add_edge('l1', 'a', 'b')
        g1.add_edge('l2', 'b', 'c')
        g1.add_edge('l3', 'b', 'd')
        tmp_file = tempfile.mkstemp("out.gv")[1]
        g1.save_to_dot(tmp_file)
        with open(tmp_file) as f:
            content_created = f.read()
        with open(GRAPH_GV) as f:
            content_expected = f.read()
        self.assertEqual(content_expected, content_created)
