from unittest import TestCase

from narraint.pubtator.document import TaggedDocument, TaggedDocumentCollection


class PubTatorDocTestCase(TestCase):

    def test_load_tagged_pubtator_doc(self):
        doc = TaggedDocument('resources/PMC1313813.txt', read_from_file=True)

        self.assertEqual(1313813, doc.id)
        self.assertEqual('Proteins are secreted by both constitutive and regulated secretory pathways in '
                         'lactating mouse mammary epithelial cells',
                         doc.title.strip())
        self.assertEqual(19, len(doc.tags))

    def test_load_untagged_pubtator_doc(self):
        doc = TaggedDocument('resources/PMC1313813Untagged.txt', read_from_file=True)

        self.assertEqual(1313813, doc.id)
        self.assertEqual('Proteins are secreted by both constitutive and regulated secretory pathways in '
                         'lactating mouse mammary epithelial cells',
                         doc.title.strip())
        self.assertEqual(0, len(doc.tags))

    def test_load_pubtator_doc_collection(self):
        col = TaggedDocumentCollection('resources/PubTatorCollection.txt')

        self.assertEqual(2, len(col.docs))

        doc = col.docs[0]
        self.assertEqual(1313813, doc.id)
        self.assertEqual(
            'Proteins are secreted by both constitutive and regulated secretory pathways in lactating mouse'
            ' mammary epithelial cells',
            doc.title.strip())
        self.assertEqual(19, len(doc.tags))

        doc = col.docs[1]
        self.assertEqual(1313814, doc.id)
        self.assertEqual(
            'Nerve growth factor nonresponsive pheochromocytoma cells: altered internalization results in '
            'signaling dysfunction',
            doc.title.strip())
        self.assertEqual(15, len(doc.tags))
