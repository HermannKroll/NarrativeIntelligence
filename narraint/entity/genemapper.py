import gzip
from itertools import islice
from narraint.config import GENE_FILE


class GeneMapper:

    def __init__(self):
        self.mapped_gene_id = 0

    #used in build_gene_id_dict for mapping gene names to human gene ids
    def build_human_gene_dict(self):
        human_gene_dict = {}
        with gzip.open(GENE_FILE, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if components[0] == '9606' and components[2] not in human_gene_dict:
                    human_gene_dict[components[2]] = components[1]
        return human_gene_dict

    #builds dictionary to map all gene ids to human gene ids, if possible
    def build_gene_id_dict(self):
        gene_id_dict = {}
        human_gene_dict = self.build_human_gene_dict()
        with gzip.open(GENE_FILE, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if components[0] != '9606' and components[1] not in human_gene_dict:
                    gene_id_dict[components[1]] = human_gene_dict[human_gene_dict[components[2]]]
        # TODO: now use pickle and save the dict wherever

    def map_to_human_gene(self, gene_id):

        # TODO: rewrite. Load dict with pickle. Check if gene_id is a key, if yes, return value, else return gene_id

        gene_name: str = ''
        mapped_gene_id = gene_id
        with gzip.open(GENE_FILE, 'rt') as f:
            
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                # find name to gene_id
                if components[1] == gene_id:
                    # check if the gene_id already belongs to human tax_id '9606' (no mapping necessary)
                    if components[0] == '9606':
                        return mapped_gene_id
                    gene_name = components[2]
                    break
            # find occurrence of gene...
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                # ...with the same name as gene_id where tax_id is '9606' for homo sapiens (human)...
                if components[2] == gene_name and components[0] == '9606':
                    # ...and if so, returns its gene id
                    return components[1]
        # otherwise, return original gene id
        return mapped_gene_id
