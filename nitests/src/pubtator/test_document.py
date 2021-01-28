import unittest
import nitests.config.config as cnf
import narraint.pubtator.document as doc
import nitests.util
from narraint.pubtator.extract import read_tagged_documents


class TestDocument(unittest.TestCase):
    def test_parse_tag_list(self):
        tags = doc.parse_tag_list(nitests.util.get_test_resource_filepath("infiles/onlytags.txt"))
        self.assertIsNotNone(tags)
        strings = [repr(tag) for tag in tags]
        self.assertIn("<Entity 0,8,prote ins,DosageForm,Desc1>", strings)
        self.assertIn("<Entity 1103,1112,proteins,DosageForm,Desc1>", strings)


    def test_Tagged_Document(self):
        in_file = nitests.util.get_test_resource_filepath("infiles/test_metadictagger/abbrev_tagged.txt")
        tagged_doc = [d for d in read_tagged_documents(in_file)][0]
        self.assertIn(doc.TaggedEntity(None, 32926486, 97,111,"ethylene oxide", "Excipient", "Ethylene oxide"),
                      tagged_doc.tags)
        self.assertIn(doc.TaggedEntity(None, 32926486, 97, 111, "Ethylene Oxide", "Chemical", "MESH:D005027"),
                      tagged_doc.tags)
        self.assertIn(doc.TaggedEntity(None, 32926486, 97, 105, "ethylene", "Excipient", "Ethylene"),
                      tagged_doc.tags)
        tagged_doc.clean_tags()
        self.assertIn(doc.TaggedEntity(None, 32926486, 97, 111, "ethylene oxide", "Excipient", "Ethylene oxide"),
                      tagged_doc.tags)
        self.assertIn(doc.TaggedEntity(None, 32926486, 97, 111, "Ethylene Oxide", "Chemical", "MESH:D005027"),
                      tagged_doc.tags)
        self.assertNotIn(doc.TaggedEntity(None, 32926486, 97, 105, "ethylene", "Excipient", "Ethylene"),
                      tagged_doc.tags)

if __name__ == '__main__':
    unittest.main()
