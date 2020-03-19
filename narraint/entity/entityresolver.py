import gzip
import logging
import pickle
from datetime import datetime
from itertools import islice

from narraint.config import GENE_FILE, GENE_INDEX_FILE, MESH_DESCRIPTORS_FILE, MESH_ID_TO_HEADING_INDEX_FILE, \
    TAXONOMY_INDEX_FILE, TAXONOMY_FILE
from narraint.mesh.data import MeSHDB


class MeshResolver:

    def __init__(self):
        self.desc2heading = {}

    def build_index(self, mesh_file, index_file):
        logging.info('Reading mesh descriptor file: {}'.format(mesh_file))
        meshdb = MeSHDB()
        meshdb.load_xml(mesh_file)
        for desc in meshdb.get_all_descs():
            self.desc2heading[desc.unique_id] = desc.heading

        logging.info('Writing index to: {}'.format(index_file))
        with open(index_file, 'wb') as f:
            pickle.dump(self.desc2heading, f)

    def load_index(self, index_file):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.desc2heading = pickle.load(f)
        logging.info('Mesh index load in {}'.format(datetime.now() - start_time))

    def descriptor_to_heading(self, descriptor_id):
        return self.desc2heading[descriptor_id]


class GeneResolver:

    def __init__(self):
        self.geneid2name = {}

    def build_index(self, gene_input, index_file):
        logging.info('Reading gene input file: {}'.format(gene_input))
        with gzip.open(gene_input, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                if len(components) == 5:
                    gene_id = components[4]
                    name = components[2]
                    self.geneid2name[gene_id] = name

        logging.info('Writing index to: {}'.format(index_file))
        with open(index_file, 'wb') as f:
            pickle.dump(self.geneid2name, f)

    def load_index(self, index_file):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.geneid2name = pickle.load(f)
        logging.info('Gene index load in {}'.format(datetime.now() - start_time))

    def gene_id_to_name(self, gene_id):
        return self.geneid2name[gene_id]


class SpeciesResolver:

    NAME_TO_LOOK_FOR = 'genbank common name'

    def __init__(self):
        self.speciesid2name = {}

    def build_index(self, species_input, index_file):
        logging.info('Reading species input file: {}'.format(species_input))
        with gzip.open(species_input, 'rt') as f:
            for line in islice(f, 1, None):
                if self.NAME_TO_LOOK_FOR in line:
                    components = line.split('\t')
                    species_id = components[0]
                    name = components[2]
                    self.speciesid2name[species_id] = name

        logging.info('Writing index to: {}'.format(index_file))
        with open(index_file, 'wb') as f:
            pickle.dump(self.speciesid2name, f)

    def load_index(self, index_file):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.speciesid2name = pickle.load(f)
        logging.info('Species index load in {}'.format(datetime.now() - start_time))

    def species_id_to_name(self, species_id):
        return self.speciesid2name[species_id]


class EntityResolver:

    __instance = None

    def __init__(self):
        self._mesh = MeshResolver()
        self._mesh.load_index(MESH_ID_TO_HEADING_INDEX_FILE)
        self._gene = GeneResolver()
        self._gene.load_index(GENE_INDEX_FILE)
        self._species = SpeciesResolver()
        self._species.load_index(TAXONOMY_INDEX_FILE)

        if self.__instance is not None:
            raise Exception('This class is a singleton - use EntityResolver.instance()')
        else:
            EntityResolver.__instance = self

    @staticmethod
    def instance():
        if EntityResolver.__instance is None:
            EntityResolver()
        return EntityResolver.__instance

    def get_name_for_var_ent_id(self, entity_id, entity_type):
        if entity_type == 'predicate':
            return entity_id  # id is already the name
        try:
            if entity_type in ['Chemical', 'Disease']:
                return self._mesh.descriptor_to_heading(entity_id.replace('MESH:', ''))
            if entity_type in ['Gene']:
                return self._gene.gene_id_to_name(entity_id)
            if entity_type == 'Species':
                return self._species.species_id_to_name(entity_id)
        except KeyError:
            return entity_id
        return entity_id


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    mesh = MeshResolver()
    mesh.build_index(MESH_DESCRIPTORS_FILE, MESH_ID_TO_HEADING_INDEX_FILE)

    gene = GeneResolver()
    gene.build_index(GENE_FILE, GENE_INDEX_FILE)

    species = SpeciesResolver()
    species.build_index(TAXONOMY_FILE, TAXONOMY_INDEX_FILE)


if __name__ == "__main__":
    main()
