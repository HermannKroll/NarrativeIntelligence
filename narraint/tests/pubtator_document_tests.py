from unittest import TestCase

from spacy.lang.en import English

from narraint.pubtator.document import TaggedDocument, TaggedDocumentCollection
from narraint.tests.test_config import get_test_resource_filepath


class PubTatorDocTestCase(TestCase):

    def test_load_tagged_pubtator_doc(self):
        content = ""
        with open(get_test_resource_filepath('PMC1313813.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content)

        self.assertEqual(1313813, doc.id)
        self.assertEqual('Proteins are secreted by both constitutive and regulated secretory pathways in '
                         'lactating mouse mammary epithelial cells',
                         doc.title.strip())
        self.assertEqual(19, len(doc.tags))

    def test_load_untagged_pubtator_doc(self):
        content = ""
        with open(get_test_resource_filepath('PMC1313813Untagged.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content)

        self.assertEqual(1313813, doc.id)
        self.assertEqual('Proteins are secreted by both constitutive and regulated secretory pathways in '
                         'lactating mouse mammary epithelial cells',
                         doc.title.strip())
        self.assertEqual(0, len(doc.tags))

    def test_load_pubtator_doc_collection(self):
        col = TaggedDocumentCollection(get_test_resource_filepath('PubTatorCollection.txt'))

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

    def test_split_sentences(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        content = ""
        with open(get_test_resource_filepath('PubMed26.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(13, len(doc.sentence_by_id))
        self.assertEqual(
            "SStudies on the action of an anticholinergic agent in combination with a tranquilizer on gastric juice secretion in mann.",
            doc.sentence_by_id[0].text)

        self.assertEqual(
            "As compared with placebo, it was not possible to establish an effect on secretion volume for oxazepam alone.",
            doc.sentence_by_id[7].text)
        self.assertEqual("The results are discussed.",
                         doc.sentence_by_id[12].text)

        content = ""
        with open(get_test_resource_filepath('PubMed54.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(16, len(doc.sentence_by_id))
        self.assertEqual("Phospholipase A2 as a probe of phospholipid distribution in erythrocyte membranes.",
                         doc.sentence_by_id[0].text)

        self.assertEqual("At pH 7.4 and 10 mM Ca2+ only stage (a) occurred.",
                         doc.sentence_by_id[5].text)

        self.assertEqual("Certain facets of this problem are discussed.",
                         doc.sentence_by_id[15].text)

    def test_find_correct_tags(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        content = ""
        with open(get_test_resource_filepath('PubMed26.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(4, len(doc.entities_by_ent_id))
        self.assertEqual(2, len(doc.entities_by_ent_id['MESH:D000284']))
        self.assertEqual(1, len(doc.entities_by_ent_id['MESH:D007262']))
        self.assertEqual(7, len(doc.entities_by_ent_id['DB00842']))
        self.assertEqual(1, len(doc.entities_by_ent_id['DB00183']))

        content = ""
        with open(get_test_resource_filepath('PubMed54.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(4, len(doc.entities_by_ent_id))
        self.assertEqual(1, len(doc.entities_by_ent_id['DB04327']))
        self.assertEqual(1, len(doc.entities_by_ent_id['DB00144']))
        self.assertEqual(1, len(doc.entities_by_ent_id['DB09341']))
        self.assertEqual(2, len(doc.entities_by_ent_id['DB11133']))

    def test_find_correct_tags_in_sentences(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        content = ""
        with open(get_test_resource_filepath('PubMed26.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(4, len(doc.sentences_by_ent_id))
        self.assertSetEqual({1}, doc.sentences_by_ent_id['MESH:D000284'])
        self.assertSetEqual({4}, doc.sentences_by_ent_id['MESH:D007262'])
        self.assertSetEqual({1, 6, 7, 8, 11}, doc.sentences_by_ent_id['DB00842'])
        self.assertSetEqual({4}, doc.sentences_by_ent_id['DB00183'])

        content = ""
        with open(get_test_resource_filepath('PubMed54.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(4, len(doc.sentences_by_ent_id))
        self.assertSetEqual({4}, doc.sentences_by_ent_id['DB04327'])
        self.assertSetEqual({4}, doc.sentences_by_ent_id['DB00144'])
        self.assertSetEqual({7}, doc.sentences_by_ent_id['DB09341'])
        self.assertSetEqual({0, 3}, doc.sentences_by_ent_id['DB11133'])

    def test_sentence_to_ent_id_mapping(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        content = ""
        with open(get_test_resource_filepath('PubMed26.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(6, len(doc.entities_by_sentence))

        self.assertEqual({'MESH:D000284', 'DB00842'}, {t.ent_id for t in doc.entities_by_sentence[1]})
        self.assertEqual({'MESH:D007262', 'DB00183'}, {t.ent_id for t in doc.entities_by_sentence[4]})
        self.assertEqual({'DB00842'}, {t.ent_id for t in doc.entities_by_sentence[6]})
        self.assertEqual({'DB00842'}, {t.ent_id for t in doc.entities_by_sentence[7]})
        self.assertEqual({'DB00842'}, {t.ent_id for t in doc.entities_by_sentence[8]})
        self.assertEqual({'DB00842'}, {t.ent_id for t in doc.entities_by_sentence[11]})

        content = ""
        with open(get_test_resource_filepath('PubMed54.txt'), 'rt') as f:
            content = f.read()
        doc = TaggedDocument(content, spacy_nlp=nlp)

        self.assertEqual(4, len(doc.sentences_by_ent_id))

        self.assertEqual({'DB04327', 'DB00144'}, {t.ent_id for t in doc.entities_by_sentence[4]})
        self.assertEqual({'DB09341'}, {t.ent_id for t in doc.entities_by_sentence[7]})
        self.assertEqual({'DB11133'}, {t.ent_id for t in doc.entities_by_sentence[0]})
        self.assertEqual({'DB11133'}, {t.ent_id for t in doc.entities_by_sentence[3]})
