import logging
import pickle
from collections import defaultdict

from narraint.config import MESH_DESCRIPTORS_FILE, DRUGBANK_ID_2_MESH_MAPPING_INDEX
from narrant.mesh.data import MeSHDB
from narrant.preprocessing.tagging.drug import DrugTaggerVocabulary

DRUGBANK_TO_MESH_DISAMBIGUATION = {
    "DB01221": "MESH:D007649",
    "DB00062": "MESH:D000075462",
    "DB11627": "MESH:D017325",
    "DB00271": "MESH:D003973",
    "DB01049": "MESH:D004877",
    "DB11151": "MESH:D012972",
    "DB00058": "MESH:D000515",
    "DB00435": "MESH:D009569",
    "DB00052": "MESH:D013006",
    "DB00158": "MESH:D005492",
    "DB11132": "MESH:D058428",
    "DB09363": "MESH:D011926",
    "DB00165": "MESH:D011736",
    "DB01022": "MESH:D010837",
    "DB03088": "MESH:D011761",
    "DB11133": "MESH:D015525",
    "DB00066": "MESH:D015292",
    "DB00102": "MESH:D000077214",
    "DB03568": "MESH:D020148",
    "DB13761": "MESH:D043322",
    "DB14292": "MESH:D029023",
    "DB00184": "MESH:D009538",
    "DB12768": "MESH:D001500",
    "DB05259": "MESH:D000068717",
    "DB14009": "MESH:D002188",
    "DB14291": "MESH:D031171",
    "DB11842": "MESH:D000804",
    "DB06779": "MESH:D017985",
    "DB00128": "MESH:D001224",
    "DB12257": "MESH:D010984",
    "DB14307": "MESH:D013662",
    "DB00048": "MESH:D028241",
    "DB08798": "MESH:D013423",
    "DB13518": "MESH:D000077322",
    "DB00475": "MESH:D002707",
    "DB00099": "MESH:D000069585",
    "DB14154": "MESH:D006046",
    "DB09337": "MESH:D000388",
    "DB12909": "MESH:D005176",
    "DB09278": "MESH:D002606",
    "DB11596": "MESH:D058766"
 }


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
        self.mesh_headings = set()
        self.dbid2meshid = {}
        self.__meshid2dbid = None

    def get_meshid_for_dbid(self, dbid: str) -> str:
        return self.dbid2meshid[dbid]

    def get_dbid_for_meshid(self, meshid: str) -> str:
        if not self.__meshid2dbid:
            logging.info('Computing  MeshID to DBID index on the fly...')
            self.__meshid2dbid = {v: k for k, v in self.dbid2meshid.items()}
        return self.__meshid2dbid[meshid]

    def compute_mappings(self):
        self._load_mesh_ontology()
        self.drug_terms2dbid = DrugTaggerVocabulary.create_drugbank_vocabulary_from_source(ignore_excipient_terms=False,
                                                                                           ignore_drugbank_chemicals=False,
                                                                                           expand_term_with_e_and_s=False)
        # compute the intersection between both vocabs
        term_intersections = set(self.drug_terms2dbid.keys()).intersection(set(self.mesh_terms2meshid.keys()))
        self.dbid2meshid.clear()
        for term in term_intersections:
            dbids = self.drug_terms2dbid[term]
            mesh_ids = self.mesh_terms2meshid[term]
            for dbid in dbids:
                if dbid in DRUGBANK_TO_MESH_DISAMBIGUATION:
                    self.dbid2meshid[dbid] = DRUGBANK_TO_MESH_DISAMBIGUATION[dbid]
                    continue
                if len(mesh_ids) == 0:
                    continue
                else:
                    mesh_desc = 'MESH:{}'.format(mesh_ids.pop())
                    if dbid in self.dbid2meshid and mesh_desc != self.dbid2meshid[dbid]:
                        # trying resolve automatically
                        if term in self.mesh_headings:
                            # choose the current the term because its a heading
                            self.dbid2meshid[dbid] = mesh_desc
                            continue
                        else:
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
            self.mesh_headings.add(mesh_head.lower())
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
