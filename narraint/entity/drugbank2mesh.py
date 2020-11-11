import logging
import pickle
from collections import defaultdict

from narraint.config import MESH_DESCRIPTORS_FILE, DRUGBANK_ID_2_MESH_MAPPING_INDEX
from narraint.mesh.data import MeSHDB
from narraint.preprocessing.tagging.drug import DrugTaggerVocabulary

DRUGBANK_TO_MESH_DISAMBIGUATION = {}


#    'DB03568': 'MESH:D020148',
#    'DB00693': 'MESH:D019793',
#    'DB00759': 'MESH:D013752',
#    'DB00091': 'MESH:D016572',
#    'DB04557': 'MESH:D016718',
#    'DB02134': 'MESH:D019820',
#    'DB03994': 'MESH:D019856',
#    'DB00536': 'MESH:D019791',
#    'DB00182': 'MESH:D000661'
# }


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
        self.mesh_terms2meshid = {}
        self.dbid2meshid = {}

    def compute_mappings(self):
        #self._load_mesh_ontology()
        self.drug_terms2dbid = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(ignore_excipient_terms=1,
                                                                                           expand_term_with_e_and_s=False)
        # compute the intersection between both vocabs
        term_intersections = set(self.drug_terms2dbid.keys()).intersection(set(self.mesh_terms2meshid.keys()))
        self.dbid2meshid.clear()
        for term in term_intersections:
            dbids = self.drug_terms2dbid[term]
            mesh_ids = self.mesh_terms2meshid[term]
            for dbid in dbids:
                if len(mesh_ids) == 0:
                    continue
                if len(mesh_ids) > 1:
                    if dbid not in DRUGBANK_TO_MESH_DISAMBIGUATION:
                        logging.warning(f'DBID {dbid} is ambigious: {mesh_ids}  -- mapping missing')
                    else:
                        self.dbid2meshid[dbid] = DRUGBANK_TO_MESH_DISAMBIGUATION[dbid]
                else:
                    mesh_desc = 'MESH:{}'.format(mesh_ids.pop())
                    if dbid in self.dbid2meshid and mesh_desc != self.dbid2meshid[dbid]:
                        logging.warning('DrugBank-ID: "{}" has already a mapping to {} (instead of {})'.format(dbid,
                                                                                                               mesh_desc,
                                                                                                               self.dbid2meshid[
                                                                                                                   dbid]))
                    # this should map only a single element
                    self.dbid2meshid[dbid] = mesh_desc

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
            for term in desc.terms:
                mesh_mappings.append((mesh_id, term.string))

        logging.info('Mesh read ({} entries)'.format(len(mesh_mappings)))
        self.mesh_terms2meshid.clear()
        for mesh_id, mesh_term in mesh_mappings:
            t = mesh_term.lower()
            if t not in self.mesh_terms2meshid:
                self.mesh_terms2meshid[t] = {mesh_id}
                continue
            else:
                if mesh_id not in self.mesh_terms2meshid[t]:
                    logging.warning('MeSH Term {} has no unique mapping: {} -> {} and {}'.format(t, mesh_term, mesh_id,
                                                                                                 self.mesh_terms2meshid[
                                                                                                     t]))
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
