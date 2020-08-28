import logging

from narraint.entity.entityresolver import EntityResolver
from narraint.entity.enttypes import GENE, SPECIES
from narraint.entity.meshontology import MeSHOntology
from narraint.queryengine.engine import QueryEngine


class EntityTagger:
    """
    EntityTagger converts a string to an entity
    Performs a simple dictionary-based lookup and returns the corresponding entity
    Builds upon the EntityResolver and computes reverse indexes,
    e.g. Gene_ID -> Gene_Name is converted to Gene_Name -> Gene_ID
    """
    def __init__(self):
        self.resolver = EntityResolver.instance()
        self.term2entity = {}
        self.mesh_ontology = MeSHOntology.instance()
        self.mesh_ontology.load_index()
        self._create_reverse_index()

    def _add_to_reverse_index(self, items, e_type, id_prefix=''):
        for e_id, e_term in items:
            term = e_term.lower().strip()
            self.term2entity[term] = (id_prefix+e_id, e_type)

    def _create_mesh_ontology_index(self, items):
        for desc_id, heading in items:
            term = heading.lower().strip()
            try:
                tree_nos = self.mesh_ontology.get_tree_numbers_for_descriptor(desc_id)
                self.term2entity[term] = tree_nos, 'MESH_ONTOLOGY'
            except KeyError:
                self.term2entity[term] = 'MESH:{}'.format(desc_id)

    def _create_reverse_index(self):
        for e_term, e_id in self.resolver.gene.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()] = (e_id, GENE)
        for e_term, e_id in self.resolver.species.get_reverse_index().items():
            self.term2entity[e_term.strip().lower()] = (e_id, SPECIES)

        self._add_to_reverse_index(self.resolver.mesh.supplement_desc2heading.items(), 'MESH', id_prefix='MESH:')
        self._create_mesh_ontology_index(self.resolver.mesh.desc2heading.items())
        self._add_to_reverse_index(self.resolver.dosageform.fid2name.items(), 'DosageForm')
        logging.info('{} different terms map to entities'.format(len(self.term2entity)))

    def tag_entity(self, term: str):
        """
        Tags an entity by given a string
        :param term: the entity term
        :return: an entity as (entity_id, entity_type)
        """
        return self.term2entity[term.lower().strip()]

