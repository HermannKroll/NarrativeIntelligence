import unittest

from narrant.preprocessing.pharmacy.drug import DrugTagger
from kgextractiontoolbox.document.document import TaggedDocument
from nitests.util import create_test_kwargs


class TestDrugVocabulary(unittest.TestCase):

    def setUp(self) -> None:
        self.tagger = DrugTagger(**create_test_kwargs())
        self.tagger.prepare()

    def test_drug_np_case(self):
        text = "A simple hydrothermal route is employed to synthesize pure copper indium disulfide (CIS) and CIS " \
               "nanoparticles (NPs) mediated by various natural plant extracts. The plant extracts used to mediate " \
               "are Azadirachta indica (neem), Ocimum sanctum (basil), Cocos nucifera (coconut), Aloe vera (aloe), " \
               "and Curcuma longa (turmeric). The tetragonal unit cell structure of as-synthesized NPs is confirmed " \
               "by X-ray diffraction. The analysis by energy-dispersive X-rays shows that all the samples are " \
               "near-stoichiometric. The morphologies of the NPs are confirmed by high-resolution scanning and " \
               "transmission modes of electron microscopy. The thermal stability of the synthesized NPs is determined " \
               "by thermogravimetric analysis. The optical energy band gap is determined from the absorption spectra " \
               "using Tauc's equation. The antimicrobial activity analysis and the estimation of the minimum " \
               "inhibitory concentration (MIC) value of the samples are performed for Escherichia coli, Pseudomonas " \
               "aeruginosa, Proteus vulgaris, Enterobacter aerogenes, and Staphylococcus aureus pathogens. It shows " \
               "that the aloe-mediated CIS NPs possess a broad inhibitory spectrum. The best inhibitory effect is " \
               "observed against S. aureus, whereas the least effect was exhibited against P. vulgaris. The least MIC " \
               "value is found for aloe-mediated CIS NPs (0.300 mg/mL) against S. aureus, P. aeruginosa, " \
               "and E. aerogenes, along with basil-mediated NPs against E. coli. The antioxidant activity study " \
               "showed that the IC50 value to inhibit the scavenging activity is maximum for the control (vitamin C) " \
               "and minimum for pure CIS NPs. The in vivo cytotoxicity study using brine shrimp eggs shows that the " \
               "pure CIS NPs are more lethal to brine shrimp than the natural extract-mediated CIS NPs. The in vitro " \
               "cytotoxicity study using the human lung carcinoma cell line (A549) shows that the IC50 value of " \
               "turmeric extract-mediated CIS NPs is minimum (15.62 ± 1.58 μg/mL). This observation reveals that " \
               "turmeric extract-mediated CIS NPs are the most potent in terms of cytotoxicity toward the A549 cell " \
               "line. "
        doc = TaggedDocument(title=text, abstract="", id=1)
        self.tagger.tag_doc(doc)
        doc.clean_tags()
        doc.sort_tags()

        self.assertEqual(0, len(doc.tags))
