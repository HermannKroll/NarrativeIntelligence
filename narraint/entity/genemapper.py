import gzip
import logging
import os
import pickle
from itertools import islice
from narraint.config import GENE_FILE, GENE_TO_HUMAN_ID_FILE, TMP_DIR


class GeneMapper:
    """
    important note: human taxonomy id is '9606'. Composition of components in GENE_FILE:
    components[0] = tax_id, components[1] = gene_id, components[2] = gene name
    """
    HUMAN_SPECIES_ID = '9606'


    __instance = None
    def __init__(self):
        if GeneMapper.__instance is not None:
            raise Exception('This class is a singleton - use EntityResolver.instance()')
        else:
            self.human_gene_dict = {}
            self.gene_to_human_id_dict = {}
            GeneMapper.__instance = self

    @staticmethod
    def instance():
        if GeneMapper.__instance is None:
            GeneMapper()
        return GeneMapper.__instance

    def _build_human_gene_name_dict(self, gene_file=GENE_FILE):
        """
        used in build_gene_id_dict() for mapping gene names to human gene ids
        :param gene_file:
        """
        self.human_gene_dict.clear()
        with gzip.open(gene_file, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if components[0] == self.HUMAN_SPECIES_ID and components[2] not in self.human_gene_dict:
                    self.human_gene_dict[components[2]] = components[1]

    def build_gene_mapper_index(self, gene_file=GENE_FILE, index_file=GENE_TO_HUMAN_ID_FILE):
        """
        builds dictionary to map all gene ids to human gene ids, if possible
        :param gene_file:
        :param index_file:
        :return:
        """
        self.gene_to_human_id_dict.clear()
        self._build_human_gene_name_dict()
        with gzip.open(gene_file, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if components[0] != self.HUMAN_SPECIES_ID and components[1] not in self.human_gene_dict:
                    self.gene_to_human_id_dict[components[1]] = self.human_gene_dict[self.human_gene_dict[components[2]]]
        with open(index_file, 'wb') as f:
            pickle.dump(self.__dict__, f)

    def load_index(self, index_file=GENE_TO_HUMAN_ID_FILE):
        """
        load the index back from file
        :param index_file:
        :return:
        """
        with open(index_file, 'rb') as f:
            self.__dict__ = pickle.load(f)

    def map_to_human_gene(self, gene_ids):
        """
        Expects gene ids which are to be mapped to human gene ids AS A LIST and returns a list of mapped ids.
        No error is returned if gene id cannot be mapped to human one
        :param gene_ids:
        :return:
        """
        mapped_gene_ids = gene_ids
        with open(GENE_TO_HUMAN_ID_FILE, 'rb') as f:
            gene_to_human_id_dict = pickle.load(f)
            for gene_id, n in gene_ids:
                mapped_gene_ids[n] = gene_to_human_id_dict.get(gene_id, gene_id)
        return mapped_gene_ids


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)

    gene_mapper = GeneMapper()
    gene_mapper.build_gene_mapper_index()

if __name__ == "__main__":
    main()
