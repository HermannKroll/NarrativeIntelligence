import gzip
import logging
import os
import pickle
from collections import defaultdict
from datetime import datetime
from itertools import islice

from narraint.backend.database import Session
from narraint.backend.models import Tag
from narraint.config import GENE_FILE, GENE_INDEX_FILE, MESH_DESCRIPTORS_FILE, MESH_ID_TO_HEADING_INDEX_FILE, \
    TAXONOMY_INDEX_FILE, TAXONOMY_FILE, DOSAGE_FID_DESCS, MESH_SUPPLEMENTARY_FILE, \
    MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE, TMP_DIR
from narraint.entity.enttypes import GENE, CHEMICAL, DISEASE, SPECIES, DOSAGE_FORM
from narraint.mesh.data import MeSHDB
from narraint.mesh.supplementary import MeSHDBSupplementary


class MeshResolver:
    """
    MeSHResolver translates MeSH descriptor ids into strings / headings
    """
    def __init__(self):
        self.desc2heading = {}
        self.supplement_desc2heading = {}

    def build_index(self, mesh_file=MESH_DESCRIPTORS_FILE, index_file=MESH_ID_TO_HEADING_INDEX_FILE,
                    mesh_supp_file=MESH_SUPPLEMENTARY_FILE, mesh_supp_index=MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE):
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

    def load_index(self, index_file=MESH_ID_TO_HEADING_INDEX_FILE,
                   supp_index_file=MESH_SUPPLEMENTARY_ID_TO_HEADING_INDEX_FILE):
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
        """
        returns a MeSH heading for a corresponding descriptor id
        throws key error if ID unknown
        :param descriptor_id: the MeSH Descriptor ID
        :return: corresponding MeSH heading
        """
        # first look in mesh db and then in supplementary
        try:
            return self.desc2heading[descriptor_id.replace('MESH:', '')]
        except KeyError:
            return self.supplement_desc2heading[descriptor_id.replace('MESH:', '')]


class GeneResolver:
    """
    GeneResolver translates NCBI Gene ids to a gene focus + gene name
    """

    def __init__(self):
        self.geneid2name = {}

    def get_reverse_index(self):
        term2entity = {}
        for e_id, (gene_focus, gene_name) in self.geneid2name.items():
            term2entity[gene_focus.strip().lower()] = str(e_id)
            term2entity[gene_name.strip().lower()] = str(e_id)
        return term2entity

    def build_index(self, gene_input=GENE_FILE, index_file=GENE_INDEX_FILE):
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
                    gene_symbol = components[2]
                    description = components[8]
                    self.geneid2name[gene_id] = (gene_symbol, description)

        logging.info('Writing index with {} keys to: {}'.format(len(self.geneid2name), index_file))
        with open(index_file, 'wb') as f:
            pickle.dump(self.geneid2name, f)

    def load_index(self, index_file=GENE_INDEX_FILE):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.geneid2name = pickle.load(f)
        logging.info('Gene index ({} keys) load in {}s'.format(len(self.geneid2name), datetime.now() - start_time))

    def gene_id_to_name(self, gene_id):
        """
        Translates a NCBI Gene ID to a Gene description + focus
        If description and locus are available, Description//Focus is returned
        else either the gene descriptor or locus
        :param gene_id: NCBI Gene ID
        :return: Description//Symbol if available, else description / symbol
        """
        try:
            gene_id_int = int(gene_id)
            symbol, description = self.geneid2name[gene_id_int]
            if symbol and description:
                return '{}//{}'.format(description, symbol)
            elif not symbol:
                return '{}'.format(description)
            else:
                return '{}'.format(symbol)
        except ValueError:
            raise KeyError('Gene ids should be ints. {} is not an int'.format(gene_id))

    def gene_id_to_symbol(self, gene_id):
        """
        Translates a NCBI Gene ID to a gene symbol like CYP3A4
        :param gene_id:
        :return:
        """
        gene_id_int = int(gene_id)
        symbol, _ = self.geneid2name[gene_id_int]
        return symbol


class SpeciesResolver:
    """
    SpeciesResolver translates a NCBI Species ID to the Species' common and scientific name
    """

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

    def build_index(self, species_input=TAXONOMY_FILE, index_file=TAXONOMY_INDEX_FILE):
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

    def load_index(self, index_file=TAXONOMY_INDEX_FILE):
        start_time = datetime.now()
        with open(index_file, 'rb') as f:
            self.speciesid2name = pickle.load(f)
        logging.info('Species index ({} keys) load in {}s'.format(len(self.speciesid2name), datetime.now() - start_time))

    def species_id_to_name(self, species_id):
        """
        Translates a NCBI Species ID to the Species' common and scientific name
        :param species_id: NCBI Species ID
        :return: Common Species Name[//Scientific Species Name (if available)]
        """
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
    """
    DosageFormResolver translates dosage form ids to their heading
    """

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
        """
        Translates a dosage form ID to it's name
        :param dosage_form_id: dosage form ID (either starting with MESH: or with FID)
        :return: Heading of the corresponding DosageForm
        """
        if dosage_form_id.startswith('MESH:'):
            return self.mesh.descriptor_to_heading(dosage_form_id)
        else:
            return self.fid2name[dosage_form_id]


class EntityResolver:
    """
    EntityResolver translates an entity id and an entity type to it's corresponding name
    EntityResolver is a singleton implementation, use EntityResolver.instance()
    Automatically loads and initialise the resolvers for MeSH, Gene, Species and DosageForms
    """

    __instance = None

    def __init__(self):
        if EntityResolver.__instance is not None:
            raise Exception('This class is a singleton - use EntityResolver.instance()')
        else:
            self.mesh = MeshResolver()
            self.mesh.load_index()
            self.gene = GeneResolver()
            self.gene.load_index()
            self.species = SpeciesResolver()
            self.species.load_index()
            self.dosageform = DosageFormResolver(self.mesh)
            EntityResolver.__instance = self

    @staticmethod
    def instance():
        if EntityResolver.__instance is None:
            EntityResolver()
        return EntityResolver.__instance

    def get_name_for_var_ent_id(self, entity_id, entity_type):
        """
        Translates an entity id and type to its name
        :param entity_id: the entity id
        :param entity_type: the entity type
        :return: uses the corresponding resolver for the entity type
        """
        if entity_id.startswith('MESH:') or entity_type in [CHEMICAL, DISEASE]:
            return self.mesh.descriptor_to_heading(entity_id)
        if entity_type == GENE:
            return self.gene.gene_id_to_name(entity_id)
        if entity_type == SPECIES:
            return self.species.species_id_to_name(entity_id)
        if entity_type == DOSAGE_FORM:
            return self.dosageform.dosage_form_to_name(entity_id)
        return entity_id


def main():
    """
    Automatically builds all indexes for the different entity resolvers
    Including: MeSHResolver, GeneResolver, SpeciesResolver and DosageFormResolver
    """
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
        
    mesh = MeshResolver()
    mesh.build_index()

    gene = GeneResolver()
    gene.build_index()

    species = SpeciesResolver()
    species.build_index()


if __name__ == "__main__":
    main()
