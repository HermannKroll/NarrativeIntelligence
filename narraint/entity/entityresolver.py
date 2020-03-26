import gzip
import logging
import pickle
from collections import defaultdict
from datetime import datetime
from itertools import islice

from narraint.config import GENE_FILE, GENE_INDEX_FILE, MESH_DESCRIPTORS_FILE, MESH_ID_TO_HEADING_INDEX_FILE, \
    TAXONOMY_INDEX_FILE, TAXONOMY_FILE, DOSAGE_FID_DESCS, MESH_SUPPLEMENTARY_FILE, \
    MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE
from narraint.mesh.data import MeSHDB
from narraint.mesh.supplementary import MeSHDBSupplementary


class MeshResolver:

    def __init__(self):
        self.desc2heading = {}
        self.supplement_desc2heading = {}

    def build_index(self, mesh_file, index_file, mesh_supp_file, mesh_supp_index):
        logging.info('Reading mesh file: {}'.format(mesh_file))
        meshdb = MeSHDB.instance()
        meshdb.load_xml(mesh_file)
        for desc in meshdb.get_all_descs():
            self.desc2heading[desc.unique_id] = desc.heading

        logging.info('Writing index ({} keys) to: {}'.format(len(self.desc2heading.keys()),
                                                             index_file))

        with open(index_file, 'wb') as f:
            pickle.dump(self.desc2heading, f)

        logging.info('Reading mesh supplementary file: {}'.format(mesh_supp_file))
        mesh_supplementary = MeSHDBSupplementary.instance()
        for desc in mesh_supplementary.get_all_descs(mesh_supp_file):
            self.supplement_desc2heading[desc.unique_id] = desc.heading
        logging.info('Writing index ({} keys) to: {}'.format(len(self.supplement_desc2heading.keys()),
                                                             mesh_supp_index))
        with open(mesh_supp_index, 'wb') as f:
            pickle.dump(self.supplement_desc2heading, f)

    def load_index(self, index_file, supp_index_file):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.desc2heading = pickle.load(f)
        logging.info('Mesh index ({} keys) load in {}s'.format(len(self.desc2heading), datetime.now() - start_time))
        start_time = datetime.now()
        with open(supp_index_file, 'rb') as f:
            self.supplement_desc2heading = pickle.load(f)
        logging.info('Mesh Supplement index ({} keys) load in {}s'.format(len(self.supplement_desc2heading),
                                                                          datetime.now() - start_time))

    def descriptor_to_heading(self, descriptor_id):
        # first look in mesh db and then in supplementary
        try:
            return self.desc2heading[descriptor_id.replace('MESH:', '')]
        except KeyError:
            return self.supplement_desc2heading[descriptor_id.replace('MESH:', '')]


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
        logging.info('Gene index ({} keys) load in {}s'.format(len(self.geneid2name), datetime.now() - start_time))

    def gene_id_to_name(self, gene_id):
        return self.geneid2name[gene_id]


class SpeciesResolver:

    NAME_COMMON = 'genbank common name'
    NAME_COMMON_SHORTCUT = "c"
    NAME_SCIENTIFIC = "scientific name"
    NAME_SCIENTIFIC_SHORTCUT = "s"

    def __init__(self):
        self.speciesid2name = defaultdict(dict)

    def build_index(self, species_input, index_file):
        logging.info('Reading species input file: {}'.format(species_input))
        with gzip.open(species_input, 'rt') as f:
            for line in islice(f, 1, None):
                if self.NAME_COMMON in line or self.NAME_SCIENTIFIC in line:
                    components = line.split('\t')
                    species_id = components[0]
                    name = components[2]

                    if self.NAME_COMMON in line:
                        self.speciesid2name[species_id][self.NAME_COMMON_SHORTCUT] = name
                    else:
                        self.speciesid2name[species_id][self.NAME_SCIENTIFIC_SHORTCUT] = name

        logging.info('Writing index to: {}'.format(index_file))
        with open(index_file, 'wb') as f:
            pickle.dump(self.speciesid2name, f)

    def load_index(self, index_file):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.speciesid2name = pickle.load(f)
        logging.info('Species index ({} keys) load in {}s'.format(len(self.speciesid2name), datetime.now() - start_time))

    def species_id_to_name(self, species_id):
        sp2name = self.speciesid2name[species_id]
        name = []
        if self.NAME_COMMON_SHORTCUT in sp2name:
            name.append(sp2name[self.NAME_COMMON_SHORTCUT])
        if self.NAME_SCIENTIFIC_SHORTCUT in sp2name:
            if name:
                name.append('/')
            name.append(sp2name[self.NAME_SCIENTIFIC_SHORTCUT])
        return ''.join(name)


class DosageFormResolver:

    def __init__(self, mesh_resolver):
        self.mesh = mesh_resolver
        self.fid2name = {}
        start_time = datetime.now()
        with open(DOSAGE_FID_DESCS, 'rt') as f:
            for line in f:
                df_id, df_head, *rest = line.strip().split('\t')
                self.fid2name[df_id] = df_head
        logging.info('DosageForm index ({} keys) load in {}s'.format(len(self.fid2name), datetime.now() - start_time))

    def dosage_form_to_name(self, dosage_form_id):
        if dosage_form_id.startswith('MESH:'):
            return self.mesh.descriptor_to_heading(dosage_form_id)
        else:
            return self.fid2name[dosage_form_id]


class EntityResolver:

    __instance = None

    def __init__(self):
        self._mesh = MeshResolver()
        self._mesh.load_index(MESH_ID_TO_HEADING_INDEX_FILE, MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE)
        self._gene = GeneResolver()
        self._gene.load_index(GENE_INDEX_FILE)
        self._species = SpeciesResolver()
        self._species.load_index(TAXONOMY_INDEX_FILE)
        self._dosageform = DosageFormResolver(self._mesh)

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
        if entity_id.startswith('MESH:') and entity_type in ['Chemical', 'Disease']:
            return self._mesh.descriptor_to_heading(entity_id)
        if entity_type == "Gene":
            return self._gene.gene_id_to_name(entity_id)
        if entity_type == 'Species':
            return self._species.species_id_to_name(entity_id)
        if entity_type == 'DosageForm':
            return self._dosageform.dosage_form_to_name(entity_id)
        # if there is no specific resolver - try with mesh
        if entity_id.startswith('MESH:'):
            return self._mesh.descriptor_to_heading(entity_id)

        return entity_id


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    mesh = MeshResolver()
    mesh.build_index(MESH_DESCRIPTORS_FILE, MESH_ID_TO_HEADING_INDEX_FILE,
                     MESH_SUPPLEMENTARY_FILE, MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE)

    gene = GeneResolver()
    gene.build_index(GENE_FILE, GENE_INDEX_FILE)

    species = SpeciesResolver()
    species.build_index(TAXONOMY_FILE, TAXONOMY_INDEX_FILE)


if __name__ == "__main__":
    main()
