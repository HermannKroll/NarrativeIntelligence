import logging
import os

from typing import List, Dict

import narraint.preprocessing.tagging.dictagger as dt
import narraint.entity.enttypes as et
from narraint.preprocessing.tagging import drug, dosage, excipient, plantfamily, drugbankchemical
from narraint.pubtator.document import TaggedEntity

"""
Modified version of the dict tagger, that can run on the vocabularies of multiple dicttaggers
"""


class MetaDicTagger(dt.DictTagger):
    __name__ = "MetaDicTagger"
    __version__ = "1.0"

    def _index_from_source(self):
        """
        Unused
        :return:
        """
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(short_name="meTa", long_name="meta dict tagger", version=None, tag_types=None,
                         index_cache=None, source_file=None, *args, **kwargs)

        self._sub_taggers: List[dt.DictTagger] = []
        self._vocabs = {}
        self.tag_types = set()
        os.makedirs(self.out_dir)

    def add_tagger(self, tagger: dt.DictTagger):
        self._sub_taggers.append(tagger)
        self.tag_types |= set(tagger.get_types())

    def prepare(self, resume=False):
        for tagger in self._sub_taggers:
            tagger.prepare()
            self._vocabs[tagger.tag_types[0]] = tagger.desc_by_term

    def generate_tag_lines(self, end, pmid, start, term):
        for entType, vocab in self._vocabs.items():
            hits = vocab.get(term)
            if hits:
                for desc in hits:
                    yield pmid, start, end, term, entType, desc

    def generate_tagged_entities(self, end, pmid, start, term, tmp_vocab=None):
        if tmp_vocab:
            tmp_hit = tmp_vocab.get(term)
            if tmp_hit:
                for entType, hit in tmp_hit:
                    yield TaggedEntity(None, pmid, start, end, term, entType, hit)
        else:
            for entType, vocab in self._vocabs.items():
                hits = vocab.get(term)
                if hits:
                    for desc in hits:
                        yield TaggedEntity((pmid, start, end, term, entType, desc))




    def get_types(self):
        return self.tag_types

class MetaDicTaggerFactory:
    tagger_by_type: Dict[str, dt.DictTagger] = {
        et.DRUG: drug.DrugTagger,
        et.DOSAGE_FORM: dosage.DosageFormTagger,
        et.EXCIPIENT: excipient.ExcipientTagger,
        et.PLANT_FAMILY: plantfamily.PlantFamilyTagger,
        et.DRUGBANK_CHEMICAL: drugbankchemical.DrugBankChemicalTagger
    }

    @staticmethod
    def get_supported_tagtypes():
        return set(MetaDicTaggerFactory.tagger_by_type.keys())

    def __init__(self, tag_types, tagger_kwargs):
        self.tag_types = tag_types
        self.tagger_kwargs = tagger_kwargs

    def create_MetaDicTagger(self):
        metatag = MetaDicTagger(**self.tagger_kwargs)
        for tag_type in self.tag_types:
            subtagger = MetaDicTaggerFactory.tagger_by_type.get(tag_type)
            if not subtagger:
                logging.warning(f"No tagging class found for tagtype {tag_type}!")
                continue
            metatag.add_tagger(subtagger(**self.tagger_kwargs))
        return metatag
