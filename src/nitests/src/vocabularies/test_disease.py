import unittest

from narrant.preprocessing.enttypes import DISEASE
from narrant.preprocessing.pharmacy.disease import DiseaseTagger
from kgextractiontoolbox.document.document import TaggedDocument
from nitests.util import create_test_kwargs


class TestDiseaseVocabulary(unittest.TestCase):

    def setUp(self) -> None:
        self.diseaseTagger = DiseaseTagger(**create_test_kwargs())
        self.diseaseTagger.prepare()

    def test_long_covid_19(self):
        text = "Post-Acute Sequelae of SARS-CoV-2 infection is a serious problem in Covid 19 infections."
        doc = TaggedDocument(title=text, abstract="", id=1)
        self.diseaseTagger.tag_doc(doc)
        doc.clean_tags()
        doc.sort_tags()

        self.assertEqual(3, len(doc.tags))
        positions = [(0, 43), (68, 76), (77, 87)]
        for idx, tag in enumerate(doc.tags):
            self.assertEqual(DISEASE, tag.ent_type)
            self.assertEqual(positions[idx][0], tag.start)
            self.assertEqual(positions[idx][1], tag.end)

        t0, t1, t2 = doc.tags[0:3]
        self.assertEqual('MESH:C000711409', t0.ent_id)
        self.assertEqual('MESH:D000086382', t1.ent_id)
        self.assertEqual('MESH:D007239', t2.ent_id)