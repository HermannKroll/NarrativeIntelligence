import logging
import pickle
from collections import defaultdict

from narraint.config import MESH_DESCRIPTORS_FILE, DRUGBANK_ID_2_MESH_MAPPING_INDEX
from narraint.mesh.data import MeSHDB
from narraint.preprocessing.tagging.drug import DrugTaggerVocabulary


class DrugBank2MeSHMapper:
    __instance = None

    @staticmethod
    def instance():
        if DrugBank2MeSHMapper.__instance is None:
            DrugBank2MeSHMapper.__instance = DrugBank2MeSHMapper()
            DrugBank2MeSHMapper.__instance.load_index()
        return DrugBank2MeSHMapper.__instance

    def __init__(self):
        self.drug_terms2dbid = {}
        self.mesh_terms2meshid = defaultdict(set)
        self.dbid2meshid = defaultdict(set)

    def compute_mappings(self):
        self._load_mesh_ontology()
        self.drug_terms2dbid = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(ignore_excipient_terms=1)
        # compute the intersection between both vocabs
        term_intersections = set(self.drug_terms2dbid.keys()).intersection(set(self.mesh_terms2meshid.keys()))
        self.dbid2meshid = defaultdict(set)
        for term in term_intersections:
            dbids = self.drug_terms2dbid[term]
            mesh_ids = self.mesh_terms2meshid[term]
            for dbid in dbids:
                if dbid in self.drug_terms2dbid:
                    raise KeyError('DBID {}has alreay a mapping to {} (instead of {})'.format(dbid, mesh_ids,
                                                                                              self.drug_terms2dbid[
                                                                                                  dbid]))
                self.dbid2meshid[dbid] = {f'MESH:{mesh_id}' for mesh_id in mesh_ids}

    def store_index(self, index_path=DRUGBANK_ID_2_MESH_MAPPING_INDEX):
        logging.info(f'Writing DrugBank2MeSH Mapping to cache: {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump(self.dbid2meshid, f)

    def load_index(self, index_path=DRUGBANK_ID_2_MESH_MAPPING_INDEX):
        logging.info(f'Loading DrugBank2MeSH Mapping from cache: {index_path}')
        with open(index_path, 'rb') as f:
            self.dbid2meshid = pickle.load(f)

    def _load_mesh_ontology(self, mesh_file=MESH_DESCRIPTORS_FILE):
        logging.info('Reading mesh file: {}'.format(mesh_file))
        meshdb = MeSHDB.instance()
        meshdb.load_xml(mesh_file)
        mesh_mappings = []
        for desc in meshdb.get_all_descs():
            mesh_id, mesh_head = desc.unique_id, desc.heading
            mesh_mappings.append((mesh_id, mesh_head))
            if mesh_id == 'D000068899':
                print('stop')
            for term in desc.terms:
                mesh_mappings.append((mesh_id, term.string))

        logging.info('Mesh read ({} entries)'.format(len(mesh_mappings)))
        self.mesh_terms2meshid = defaultdict(set)
        for mesh_id, mesh_term in mesh_mappings:
            mesh_term_lower = mesh_term.lower()
            terms = {mesh_term_lower, f'{mesh_term_lower}e', f'{mesh_term_lower}s'}
            for t in terms:
                if t in self.mesh_terms2meshid and mesh_id not in self.mesh_terms2meshid[t]:
                    print('MeSH Term {} has no unique mapping: {} -> {} and {}'.format(t, mesh_term, mesh_id,
                                                                                       self.mesh_terms2meshid[t]))

                self.mesh_terms2meshid[t].add(mesh_id)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    drug2mesh = DrugBank2MeSHMapper()
    drug2mesh.compute_mappings()
    drug2mesh.store_index()


if __name__ == "__main__":
    main()
