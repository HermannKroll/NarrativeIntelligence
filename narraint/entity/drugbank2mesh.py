import logging
import pickle
from collections import defaultdict
from datetime import datetime

import lxml.etree as ET

from narraint import config
from narraint.config import MESH_DESCRIPTORS_FILE, DRUGBANK_ID_2_MESH_MAPPING_INDEX
from narraint.mesh.data import MeSHDB
from narraint.progress import print_progress_with_eta

DRUG_MIN_NAME_LENGTH = 3
DRUG_MAX_PER_PRODUCT = 2


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
        self._load_drugbank_terms()
        # compute the intersection between both vocabs
        term_intersections = set(self.drug_terms2dbid.keys()).intersection(set(self.mesh_terms2meshid.keys()))
        self.dbid2meshid = defaultdict(set)
        for term in term_intersections:
            dbids = self.drug_terms2dbid[term]
            mesh_ids = self.mesh_terms2meshid[term]
            for dbid in dbids:
                if dbid in self.drug_terms2dbid:
                    raise KeyError('DBID {}has alreay a mapping to {} (instead of {})'.format(dbid, mesh_ids,
                                                                                              self.drug_terms2dbid[dbid]))
                self.dbid2meshid[dbid] = {f'MESH:{mesh_id}' for mesh_id in mesh_ids}

    def store_index(self, index_path=DRUGBANK_ID_2_MESH_MAPPING_INDEX):
        logging.info(f'Writing DrugBank2MeSH Mapping to cache: {index_path}')
        with open(index_path, 'wb') as f:
            pickle.dump(self.dbid2meshid, f)

    def load_index(self, index_path=DRUGBANK_ID_2_MESH_MAPPING_INDEX):
        logging.info(f'Loading DrugBank2MeSH Mapping from cache: {index_path}')
        with open(index_path, 'rb') as f:
            self.dbid2meshid = pickle.load(f)

    def _load_drugbank_terms(self):
        logging.info("checking total number of drugs...")
        # TODO real check
        drug_number = 13581
        logging.info(f"found {drug_number}.")
        start = datetime.now()
        drugs_found = 0
        logging.info(f"")
        pref = '{http://www.drugbank.ca}'
        desc_by_term = {}
        for event, elem in ET.iterparse(config.DRUGBASE_XML_DUMP, tag=f'{pref}drug'):
            desc = ''
            for dbid in elem.findall(f'{pref}drugbank-id'):
                if dbid.attrib.get('primary'):
                    desc = dbid.text
                    break
            if desc == '':
                continue
            drugs_found += 1
            print_progress_with_eta("building index...", drugs_found, drug_number, start, print_every_k=100)
            description_text = elem.find(f'{pref}description').text
            if description_text and 'allergen' in description_text.lower()[0:20]:
                continue
            name_elements = list(elem.findall(f'{pref}name'))
            synonyms = elem.find(f'{pref}synonyms')
            if synonyms is not None:
                name_elements += list(synonyms.findall(f'{pref}synonym'))
            products = elem.find(f'{pref}products')
            if products is not None:
                for product in products.findall(f'{pref}product'):
                    name = product.find(f'{pref}name')
                    if name is not None:
                        name_elements.append(name)
            exp_props = elem.find(f'{pref}experimental-properties')
            if exp_props is not None:
                for exp_prop in exp_props:
                    if exp_prop.find(f'{pref}kind').text == "Molecular Formula":
                        name_elements.append(exp_prop.find(f'{pref}value'))
            names = {ne.text for ne in name_elements if len(ne.text) >= DRUG_MIN_NAME_LENGTH}
            names = {n.lower() for n in names}
            names = names | {f"{n}s" for n in names} | {f"{n}e" for n in names}
            for n in names:
                if n in desc_by_term:
                    desc_by_term[n].add(desc)
                else:
                    desc_by_term[n] = {desc, }

        if DRUG_MAX_PER_PRODUCT > 0:
            self.drug_terms2dbid = {k: v
                                 for k, v in desc_by_term.items()
                                 if len(v) <= DRUG_MAX_PER_PRODUCT}

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
        self.mesh_terms2meshid = defaultdict(set)
        for mesh_id, mesh_term in mesh_mappings:
            mesh_term_lower = mesh_term.lower()
            terms = {mesh_term_lower, f'{mesh_term_lower}e', f'{mesh_term_lower}s'}
            for t in terms:
                if t in self.mesh_terms2meshid and mesh_id not in self.mesh_terms2meshid[t]:
                    print('MeSH Term {} has no unique mapping: {} -> {} and {}'.format(t, mesh_term, mesh_id, self.mesh_terms2meshid[t]))

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
