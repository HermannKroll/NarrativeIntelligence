import os
from unittest import TestCase

from translate import translate_file, clean_text


class Test(TestCase):
    def setUp(self):
        self.file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/gnorm_problem_files/u2028.nxml")

    def test_clean_text_normal(self):
        text = " Line 1\nLine ||2\u2028Line 3 "
        text_expected = "Line 1 Line 2 Line 3"
        self.assertEqual(clean_text(text), text_expected)

    def test_clean_text_raise_error_None(self):
        with self.assertRaises(AttributeError):
            clean_text(None)

    def test_translate_file_unicode_u2028_removed(self):
        with open(self.file) as f:
            content_nxml = f.read()
        self.assertEqual(content_nxml.count("&#x02028;"), 12)
        content_pubtator = translate_file(self.file)
        self.assertEqual(content_pubtator.count("\u2028"), 0)
