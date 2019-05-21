import os
from unittest import TestCase

from tag import get_next_pivot


class TestHelper(TestCase):
    def setUp(self):
        self.example_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/example_dir")

    def test_get_next_pivot_file_not_exists(self):
        pivot = get_next_pivot(self.example_dir, "file0.txt")
        self.assertEqual(pivot, "file1.txt")
        pivot = get_next_pivot(self.example_dir, "other.txt")
        self.assertEqual(pivot, None)

    def test_get_next_pivot_file_exists(self):
        pivot = get_next_pivot(self.example_dir, "file1.txt")
        self.assertEqual(pivot, "file2.txt")
        pivot = get_next_pivot(self.example_dir, "file2.txt")
        self.assertEqual(pivot, None)
