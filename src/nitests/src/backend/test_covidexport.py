import unittest
from narant.backend.covidexport import create_sanitized_index

class TestCovidExport(unittest.TestCase):
    def test_create_sanitized_index(self):
        text = "Das ist ein schön€r Tag!"
        tag_start = 8
        tag_end = 18
        index = create_sanitized_index(text)
        san_start = index[tag_start]
        san_end = index[tag_end]
        assert text[san_start:san_end] == "ein schön€r"
