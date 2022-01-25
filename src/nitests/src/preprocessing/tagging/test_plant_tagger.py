import unittest

import narrant.pubtator.document as doc
from narrant.preprocessing.enttypes import PLANT_FAMILY_GENUS
from narrant.preprocessing.pharmacy.plantfamilygenus import PlantFamilyGenusTagger
from nitests.util import create_test_kwargs


class TestPlantTagger(unittest.TestCase):

    def setUp(self) -> None:
        self.tagger = PlantFamilyGenusTagger(**create_test_kwargs())
        self.tagger.prepare()

    def test_text_tagging_family(self):
        text = "Vitaceae is a wonderful plant."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(8, tag.end)
        self.assertEqual("Vitaceae", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_family_and_genus(self):
        text = "Vitaceae is a wonderful plant. Acacia is it too."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(2, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(8, tag.end)
        self.assertEqual("Vitaceae", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

        tag = doc1.tags[1]
        self.assertEqual(31, tag.start)
        self.assertEqual(37, tag.end)
        self.assertEqual("Acacia", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_family_and_genus_brackets(self):
        text = "The wonderful plant (Vitaceae, test), is green."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(21, tag.start)
        self.assertEqual(29, tag.end)
        self.assertEqual("Vitaceae", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_genus_without_family(self):
        text = "Bla is a wonderful plant. Acacia is it too."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(0, len(doc1.tags))

    def test_text_tagging_genus_with_plant_rule(self):
        text = "Acacia is used in traditional chinese medicine."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(0, tag.start)
        self.assertEqual(6, tag.end)
        self.assertEqual("Acacia", tag.ent_id)
        self.assertEqual(PLANT_FAMILY_GENUS, tag.ent_type)

    def test_text_tagging_clean_only_plants(self):
        text = "Bla is a wonderful plant. Acacia is it too."

        doc1 = doc.TaggedDocument(title=text, abstract="", id=1)
        doc1.tags.append(doc.TaggedEntity(document=1, start=20, end=24, ent_id="Plant", ent_type="Misc",
                                          text="plant"))
        self.tagger.tag_doc(doc1)
        doc1.sort_tags()

        self.assertEqual(1, len(doc1.tags))
        tag = doc1.tags[0]
        self.assertEqual(20, tag.start)
        self.assertEqual(24, tag.end)
        self.assertEqual("Plant", tag.ent_id)
        self.assertEqual("Misc", tag.ent_type)

    def test_monimiaceae_sentence_end(self):
        t1 = "matica (Monimiaceae)."
        doc_test = doc.TaggedDocument(title=t1, abstract="", id=1)
        self.tagger.tag_doc(doc_test)
        doc_entity_ids = set([e.ent_id for e in doc_test.tags])
        self.assertIn('Monimiaceae', doc_entity_ids)

    def test_monimiaceae_examples(self):
        t1 = "Four new alkaloids, (R)-nomimantharine trifluoroacetate (2), 12-demethylphaeantharine trifluoroacetate (3), nominanthranal trifluoroacetate (4), and the enolic form of 1-hydroxy-6,7-dimethoxy-2-methylisoquinoline trifluoroacetate (5), together with the known dimeric alkaloid phaeantharine trifluoroacetate (1), have been isolated from the extract of the leaves of the rainforest tree Doryphora aromatica (Monimiaceae)."
        t2 = "The Chilean plants Discaria chacaye, Talguenea quinquenervia (Rhamnaceae), Peumus boldus (Monimiaceae), and Cryptocarya alba (Lauraceae) were evaluated against Codling moth: Cydia pomonella L. (Lepidoptera: Tortricidae) and fruit fly Drosophila melanogaster (Diptera: Drosophilidae), which is one of the most widespread and destructive primary pests of Prunus (plums, cherries, peaches, nectarines, apricots, almonds), pear, walnuts, and chestnuts, among other."
        t3 = "Peumus boldus Molina (Monimiaceae), commonly referred to as 'boldo', is used in traditional Chilean medicine to treat hepatic and gastrointestinal diseases."
        t4 = "Extracts of another 19 species showed moderate neutralization (21-72%) at doses up to 4 mg/mouse, e.g. the whole plants of Aristolochia grandiflora (Aristolochiaceae), Columnea kalbreyeriana (Gesneriaceae), Sida acuta (Malvaceae), Selaginella articulata (Selaginellaceae) and Pseudoelephantopus spicatus (Asteraceae); rhizomes of Renealmia alpinia (Zingiberaceae); the stem of Strychnos xinguensis (Loganiaceae); leaves, branches and stems of Hyptis capitata (Lamiaceae), Ipomoea cairica (Convolvulaceae), Neurolaena lobata (Asteraceae), Ocimum micranthum (Lamiaceae), Piper pulchrum (Piperaceae), Siparuna thecaphora (Monimiaceae), Castilla elastica (Moraceae) and Allamanda cathartica (Apocynaceae); the macerated ripe fruits of Capsicum frutescens (Solanaceae); the unripe fruits of Crescentia cujete (Bignoniaceae); leaves and branches of Piper arboreum (Piperaceae) and Passiflora quadrangularis (Passifloraceae)."
        t5 = "From a lipophilic extract of leaves of Siparuna andina (Monimiaceae), which exhibited antiplasmodial activity in vitro, two new compounds have been isolated: sipandinolide (1), a compound with a novel type of carbon skeleton and (-)-cis-3-acetoxy-4',5,7-trihydroxyflavanone (2)."
        t6 = "Ascaridole, an asymmetric monoterpene endoperoxide with anthelmintic properties, occurs as a major constituent (60-80%) in the volatile oil of American wormseed fruit (Chenopodium ambrosioides: Chenopodiaceae), and as a lesser component in the leaf pocket oil of the boldo tree (Peumus boldus: Monimiaceae)."
        tests = [t1, t2, t3, t4, t5, t6]

        for t in tests:
            doc_test = doc.TaggedDocument(title=t, abstract="", id=1)
            self.tagger.tag_doc(doc_test)
            doc_entity_ids = set([e.ent_id for e in doc_test.tags])
            self.assertIn('Monimiaceae', doc_entity_ids)
