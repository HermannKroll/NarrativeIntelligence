import logging
import os
import pickle
from collections import defaultdict
from datetime import datetime

from narraint.config import MESH_DESCRIPTORS_FILE, MESH_ONTOLOGY_INDEX_FILE
from narraint.mesh.data import MeSHDB, Descriptor
from narraint.progress import print_progress_with_eta

MESH_TREE_NAMES = dict(
    A="Anatomy",
    B="Organisms",
    C="Diseases",
    D="Chemicals and Drugs",
    E="Analytical, Diagnostic and Therapeutic Techniques, and Equipment",
    F="Psychiatry and Psychology",
    G="Phenomena and Processes",
    H="Disciplines and Occupations",
    I="Anthropology, Education, Sociology, and Social Phenomena",
    J="Technology, Industry, and Agriculture",
    K="Humanities",
    L="Information Science",
    M="Named Groups",
    N="Health Care",
    V="Publication Characteristics",
    Z="Geographicals"
)


class MeSHOntology:
    """
    class to store the mesh ontology in a efficient tree structure
    this class is a singleton - use MeSHOntology.instance()
    """

    __instance = None

    def __init__(self):
        if MeSHOntology.__instance is not None:
            raise Exception('This class is a singleton - use EntityOntology.instance()')
        else:
            self.treeno2desc = {}
            self.descriptor2treeno = {}
            self.load_index()
            MeSHOntology.__instance = self

    @staticmethod
    def instance():
        if MeSHOntology.__instance is None:
            MeSHOntology()
        return MeSHOntology.__instance

    def _clear_index(self):
        """
        Clear the index by removing all entries from dictionaries
        :return: Nothing
        """
        self.treeno2desc = {}
        self.descriptor2treeno = {}

    def _add_descriptor_for_tree_no(self, descriptor_id, descriptor_heading, tree_no: str):
        """
        Stores the tree number as an index for the descriptor
        :param descriptor_id: MeSH Descriptor id
        :param descriptor_heading: MeSH Descriptor heading
        :param tree_no: Tree number as a String (e.g. C01.622....
        :return: Nothing
        """
        if tree_no in self.treeno2desc:
            raise KeyError('tree number is already mapped to: {}'.format(self.treeno2desc[tree_no] ))
        self.treeno2desc[tree_no] = (descriptor_id, descriptor_heading)

    def find_descriptors_start_with_tree_no(self, tree_no: str) -> [(str, str)]:
        """
        Finds all descriptors which are in a tree starting with the tree number
        :param tree_no: tree number which should be the start of the descriptors
        :return: a list of descriptors (id, heading)
        """
        results = []
        visited = set()
        for d_tree_no, (d_id, d_heading) in self.treeno2desc.items():
            if d_id not in visited:
                if d_tree_no.startswith(tree_no):
                    results.append((d_id, d_heading))
                    visited.add(d_id)
        return results

    def get_descriptor_for_tree_no(self, tree_no: str) -> (str, str):
        """
        Gets a MeSH Descriptor for a tree number
        :param tree_no: MeSH tree number
        :return: (MeSH Descriptor id, MeSH Descriptor heading)
        """
        return self.treeno2desc[tree_no]

    def _add_tree_number_for_descriptor(self, descriptor_id: str, tree_no: str):
        """
        Add a tree number for a descriptor
        :param descriptor_id: MeSH descriptor id
        :param tree_no: Tree number for this descriptor
        :return:
        """
        if descriptor_id in self.descriptor2treeno:
            self.descriptor2treeno[descriptor_id].append(tree_no)
        else:
            self.descriptor2treeno[descriptor_id] = [tree_no]

    def get_tree_numbers_for_descriptor(self, descriptor_id) -> [str]:
        """
        Returns a list of tree numbers for a descriptor id
        :param descriptor_id: MeSH descriptor id
        :return: List of tree numbers
        """
        return self.descriptor2treeno[descriptor_id]

    def build_index_from_mesh(self, mesh_file=MESH_DESCRIPTORS_FILE):
        """
        Builds the index from a raw MeSH XML file
        :param mesh_file: Path to a MeSH XML file (default is the default MeSH descriptor path in the project config)
        :return: Nothing
        """
        self._clear_index()
        logging.info('Loading MeSH...')
        mesh = MeSHDB.instance()
        mesh.load_xml(mesh_file)
        descs = mesh.get_all_descs()
        logging.info('Processing descriptors...')
        start_time = datetime.now()
        descriptor_count = len(descs)
        for idx, desc in enumerate(descs):
            for tn in desc.tree_numbers:
                self._add_descriptor_for_tree_no(desc.unique_id, desc.heading, tn)
                self._add_tree_number_for_descriptor(desc.unique_id, tn)
            print_progress_with_eta("building mesh ontology", idx, descriptor_count, start_time, print_every_k=1)
        logging.info('MeSH Ontology complete')

    def store_index(self, index_path=MESH_ONTOLOGY_INDEX_FILE):
        """
        Pickles the whole MeSH ontology to a file
        :param index_path: Path for index (default in project's config)
        :return: Nothing
        """
        with open(index_path, 'wb') as f:
            pickle.dump(self.__dict__, f)

    def load_index(self, index_path=MESH_ONTOLOGY_INDEX_FILE):
        """
        Loads the whole ontology from a pickle dump
        :param index_path: Path for pickle dump (default in project's config)
        :return: None
        """
        with open(index_path, 'rb') as f:
            self.__dict__ = pickle.load(f)

    def retrieve_subdescriptors(self, decriptor_id: str) -> [(str)]:
        """
        retrieves a list of all sub-descriptors for a given descriptor
        :param decriptor_id: a mesh descriptor id
        :return: a list of sub-descritor ids
        """
        tree_nos = self.get_tree_numbers_for_descriptor(descriptor_id=decriptor_id)
        sub_descriptors = set()
        for t_n in tree_nos:
            for res in self.find_descriptors_start_with_tree_no(t_n):
                sub_descriptors.add(res)
        return sub_descriptors


    def get_name_for_tree(self, tree_start_character):
        """
        Returns the official name for the mesh tree name
        :param tree_start_character: the starting character
        :return: the official mesh tree name
        """
        return MESH_TREE_NAMES[tree_start_character]


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Computing entity ontology index...')
    entity_ontology = MeSHOntology.instance()
    entity_ontology.build_index_from_mesh()
    logging.info('Storing index to: {} '.format(MESH_ONTOLOGY_INDEX_FILE))
    entity_ontology.store_index()
    logging.info('Finished')


if __name__ == "__main__":
    main()
