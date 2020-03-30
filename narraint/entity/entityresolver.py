import gzip
import logging
import pickle
from collections import defaultdict
from datetime import datetime
from itertools import islice

from narraint.backend.database import Session
from narraint.backend.models import Tag
from narraint.config import GENE_FILE, GENE_INDEX_FILE, MESH_DESCRIPTORS_FILE, MESH_ID_TO_HEADING_INDEX_FILE, \
    TAXONOMY_INDEX_FILE, TAXONOMY_FILE, DOSAGE_FID_DESCS, MESH_SUPPLEMENTARY_FILE, \
    MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE
from narraint.entity.enttypes import GENE
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

    def get_reverse_index(self):
        term2entity = {}
        for e_id, (gene_focus, gene_name) in self.geneid2name.items():
            term2entity[gene_focus.strip().lower()] = str(e_id)
            term2entity[gene_name.strip().lower()] = str(e_id)
        return term2entity

    def build_index(self, gene_input, index_file):
        logging.info('Querying entity ids in db...')
        session = Session.get()
        gene_ids_in_db = set()
        q = session.query(Tag.ent_id.distinct()).filter(Tag.ent_type == GENE)
        for r in session.execute(q):
            try:
                gene_ids_in_db.add(int(r[0]))
            except ValueError:
                continue
        logging.info('{} gene ids retrieved'.format(len(gene_ids_in_db)))

        logging.info('Reading gene input file: {}'.format(gene_input))
        with gzip.open(gene_input, 'rt') as f:
            for line in islice(f, 1, None):
                components = line.strip().split('\t')
                gene_id = int(components[1])
                if gene_id in gene_ids_in_db:
                    gene_locus = components[2]
                    description = components[8]
                    self.geneid2name[gene_id] = (gene_locus, description)

        logging.info('Writing index with {} keys to: {}'.format(len(self.geneid2name), index_file))
        with open(index_file, 'wb') as f:
            pickle.dump(self.geneid2name, f)

    def load_index(self, index_file):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.geneid2name = pickle.load(f)
        logging.info('Gene index ({} keys) load in {}s'.format(len(self.geneid2name), datetime.now() - start_time))

    def gene_id_to_name(self, gene_id):
        try:
            gene_id_int = int(gene_id)
            locus, description = self.geneid2name[gene_id_int]
            if locus and description:
                return '{}//{}'.format(description, locus)
            elif not locus:
                return '{}'.format(description)
            else:
                return '{}'.format(locus)
        except ValueError:
            raise KeyError('Gene ids should be ints. {} is not an int'.format(gene_id))


class SpeciesResolver:

    NAME_COMMON = 'genbank common name'
    NAME_COMMON_SHORTCUT = "c"
    NAME_SCIENTIFIC = "scientific name"
    NAME_SCIENTIFIC_SHORTCUT = "s"

    def __init__(self):
        self.speciesid2name = defaultdict(dict)

    def get_reverse_index(self):
        s2n = dict()
        for sid, n_dict in self.speciesid2name.items():
            if self.NAME_COMMON_SHORTCUT in n_dict:
                s2n[n_dict[self.NAME_COMMON_SHORTCUT]] = sid
            if self.NAME_SCIENTIFIC_SHORTCUT in n_dict:
                s2n[n_dict[self.NAME_SCIENTIFIC_SHORTCUT]] = sid
        return s2n

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
                name.append('//')
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
        if EntityResolver.__instance is not None:
            raise Exception('This class is a singleton - use EntityResolver.instance()')
        else:
            self.mesh = MeshResolver()
            self.mesh.load_index(MESH_ID_TO_HEADING_INDEX_FILE, MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE)
            self.gene = GeneResolver()
            self.gene.load_index(GENE_INDEX_FILE)
            self.species = SpeciesResolver()
            self.species.load_index(TAXONOMY_INDEX_FILE)
            self.dosageform = DosageFormResolver(self.mesh)
            EntityResolver.__instance = self

    @staticmethod
    def instance():
        if EntityResolver.__instance is None:
            EntityResolver()
        return EntityResolver.__instance

    def get_name_for_var_ent_id(self, entity_id, entity_type):
        if entity_id.startswith('MESH:') or entity_type in ['Chemical', 'Disease']:
            return self.mesh.descriptor_to_heading(entity_id)
        if entity_type == "Gene":
            return self.gene.gene_id_to_name(entity_id)
        if entity_type == 'Species':
            return self.species.species_id_to_name(entity_id)
        if entity_type == 'DosageForm':
            return self.dosageform.dosage_form_to_name(entity_id)
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
