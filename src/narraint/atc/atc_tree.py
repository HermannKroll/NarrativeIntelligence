import csv
import logging
from collections import defaultdict
from itertools import islice
from typing import Set

from narraint.config import CHEMBL_ATC_CLASSIFICATION_FILE


def _prepare_atc_class_name(atc_class_name: str):
    """
    Lowers and then capitalizes each word of an atc class name
    :param atc_class_name: atc class name
    :return: word-capitalized version of the string
    """
    return ' '.join([s.lower().capitalize() for s in atc_class_name.split(' ')])


class ATCTree:
    __instance = None

    @staticmethod
    def instance(load_index=True):
        if ATCTree.__instance is None:
            ATCTree(load_index=load_index)
        return ATCTree.__instance

    def __init__(self, load_index=True):
        if ATCTree.__instance is not None:
            raise Exception('This class is a singleton - use ATCTree.instance()')
        else:
            self.atcclass2chembl = defaultdict(set)
            self.atcclassname2chembl = defaultdict(set)
            self.atcclass2name = {}

            if load_index:
                self.load_atc_tree()

            self.chembl2atcclass = defaultdict(set)
            for atc_class, chembl_ids in self.atcclass2chembl.items():
                for chembl in chembl_ids:
                    self.chembl2atcclass[chembl].add(atc_class.upper())

            ATCTree.__instance = self

    def get_classes_for_chembl_id(self, chembl_id: str) -> Set[str]:
        return self.chembl2atcclass[chembl_id]

    def get_drugs_for_atc_class(self, atc_class: str) -> Set[str]:
        return self.atcclass2chembl[atc_class.strip().lower()]

    def get_drugs_for_atc_class_name(self, atc_class_name: str) -> Set[str]:
        return self.atcclassname2chembl[atc_class_name.strip().lower()]

    def load_atc_tree(self, file=CHEMBL_ATC_CLASSIFICATION_FILE):
        logging.info('Reading ATC Chembl information...')
        with open(file, 'rt') as f:
            reader = csv.reader(f, delimiter=',')
            for row in islice(reader, 1, None):
                c_id, who_name, level1, level2, level3, level4, level5, \
                level1_desc, level2_desc, level3_desc, level4_desc, = row

                for level in [level1, level2, level3, level4, level5]:
                    self.atcclass2chembl[level.strip().lower()].add(c_id)
                for level_desc in [level1_desc, level2_desc, level3_desc, level4_desc]:
                    self.atcclassname2chembl[level_desc.strip().lower()].add(c_id)

                self.atcclass2name[level1] = _prepare_atc_class_name(level1_desc)
                self.atcclass2name[level2] = _prepare_atc_class_name(level2_desc)
                self.atcclass2name[level3] = _prepare_atc_class_name(level3_desc)
                self.atcclass2name[level4] = _prepare_atc_class_name(level4_desc)
        logging.info('ATC tree built')
