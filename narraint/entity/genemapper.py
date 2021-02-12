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
            try:
                self.load_index()
            except FileExistsError and FileNotFoundError:
                logging.warning('No GeneMapper Index file was found')
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
                gene_id = int(components[1])
                gene_name = components[2]
                if components[0] == self.HUMAN_SPECIES_ID and gene_name not in self.human_gene_dict:
                    self.human_gene_dict[gene_name] = gene_id


    def build_gene_mapper_index(self, gene_file=GENE_FILE, index_file=GENE_TO_HUMAN_ID_FILE):
        """
        builds dictionary to map all gene ids to human gene ids, if possible
        :param gene_file:
        :param index_file:
        :return:
        """
        logging.info('Computing index...')
        self.gene_to_human_id_dict.clear()
        self._build_human_gene_name_dict()
        with gzip.open(gene_file, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                species_id, gene_id, gene_name = components[0:3]
                gene_id = int(gene_id)
                if species_id != self.HUMAN_SPECIES_ID and gene_name in self.human_gene_dict:
                    self.gene_to_human_id_dict[gene_id] = self.human_gene_dict[gene_name]
        with open(index_file, 'wb') as f:
            pickle.dump(self.__dict__, f)
        logging.info('Index stored in {}'.format(index_file))

    def load_index(self, index_file=GENE_TO_HUMAN_ID_FILE):
        """
        load the index back from file
        :param index_file:
        :return:
        """
        with open(index_file, 'rb') as f:
            self.__dict__ = pickle.load(f)
        logging.info('Index for gene mapper load from {} ({} keys)'.format(index_file, len(self.gene_to_human_id_dict)))

    def map_to_human_gene(self, gene_id):
        """
        Expects a gene id which is mapped to the corresponding humen gene
        Keyerror is thrown if no mapping exists
        :param gene_id: gene id which should be mapped to the human gene id
        :return: human gene id
        """
        return self.gene_to_human_id_dict[int(gene_id)]


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    gene_mapper = GeneMapper()
    gene_mapper.build_gene_mapper_index()


if __name__ == "__main__":
    main()
