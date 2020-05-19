import gzip
import pickle
from itertools import islice
from narraint.config import GENE_FILE, GENE_TO_HUMAN_ID_FILE


# important note: human taxonomy id is '9606'. Composition of components in GENE_FILE:
# components[0] = tax_id, components[1] = gene_id, components[2] = gene name
class GeneMapper:

    def __init__(self):
        self.mapped_gene_id = 0

    # used in build_gene_id_dict() for mapping gene names to human gene ids
    def build_human_gene_name_dict(self):
        human_gene_dict = {}
        with gzip.open(GENE_FILE, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if components[0] == '9606' and components[2] not in human_gene_dict:
                    human_gene_dict[components[2]] = components[1]
        return human_gene_dict

    # builds dictionary to map all gene ids to human gene ids, if possible
    def build_gene_id_dict(self):
        gene_to_human_id_dict = {}
        human_gene_name_dict = self.build_human_gene_name_dict()
        with gzip.open(GENE_FILE, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if components[0] != '9606' and components[1] not in human_gene_name_dict:
                    gene_to_human_id_dict[components[1]] = human_gene_name_dict[human_gene_name_dict[components[2]]]
        with open(GENE_TO_HUMAN_ID_FILE, 'wb') as f:
            pickle.dump(gene_to_human_id_dict, f)

    # Expects gene ids which are to be mapped to human gene ids AS A LIST and returns a list of mapped ids.
    # No error is returned if gene id cannot be mapped to human one
    def map_to_human_gene(self, gene_ids):

        mapped_gene_ids = gene_ids
        with open(GENE_TO_HUMAN_ID_FILE, 'rb') as f:
            gene_to_human_id_dict = pickle.load(f)
            for gene_id, n in gene_ids:
                mapped_gene_ids[n] = gene_to_human_id_dict.get(gene_id, gene_id)
        return mapped_gene_ids
