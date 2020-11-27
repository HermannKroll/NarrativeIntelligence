import unittest
import nitests.config.config as cnf
import narraint.pubtator.document as doc
import nitests.util


class TestDocument(unittest.TestCase):
    def test_parse_tag_list(self):
        tags = doc.parse_tag_list(nitests.util.get_test_resource_filepath("infiles/onlytags.txt"))
        self.assertIsNotNone(tags)
        strings = [str(tag) for tag in tags]
        self.assertIn("<Entity 0,8,prote ins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1103,1112,proteins,DosageForm,Desc1>", strings)


if __name__ == '__main__':
    unittest.main()
