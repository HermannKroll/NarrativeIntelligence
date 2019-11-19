import os

from preprocessing.tests.base import BaseTestCase


class Test(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.file = os.path.join(self.resource_dir, "gnorm_problem_files/u2028.nxml")

    # def test_clean_text_normal(self):
    #     text = " Line 1\nLine ||2\u2028Line 3 "
    #     text_expected = "Line 1 Line 2 Line 3"
    #     self.assertEqual(clean_text(text), text_expected)
    #
    # def test_clean_text_raise_error_None(self):
    #     with self.assertRaises(AttributeError):
    #         clean_text(None)

    # def test_translate_file_unicode_u2028_removed(self):
    #     with open(self.file) as f:
    #         content_nxml = f.read()
    #     self.assertEqual(content_nxml.count("&#x02028;"), 12)
    #     content_pubtator = translate_file(self.file)
    #     self.assertEqual(content_pubtator.count("\u2028"), 0)
