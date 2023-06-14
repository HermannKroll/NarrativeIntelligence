from __future__ import annotations

from narrant.entity.entityresolver import EntityResolver, MeshResolver, GeneResolver, SpeciesResolver, \
    DosageFormResolver, ChEMBLDatabaseResolver, VaccineResolver


class EntityResolverJCDL:
    """
    EntityResolver translates an entity id and an entity type to it's corresponding name
    EntityResolver is a singleton implementation, use EntityResolver.instance()
    Automatically loads and initialise the resolvers for MeSH, DrugbankIDs, Gene, Species and DosageForms
    """

    __instance = None

    def __init__(self):
        if EntityResolverJCDL.__instance is not None:
            raise Exception('This class is a singleton - use EntityResolver.instance()')
        else:
            self.mesh = MeshResolver()
            self.mesh.load_index()
            self.gene = GeneResolver()
            self.gene.load_index()
            self.species = SpeciesResolver()
            self.species.load_index()
            self.dosageform = DosageFormResolver(self.mesh)
            self.mesh_ontology = None
            self.chebml = ChEMBLDatabaseResolver()
            self.chebml.load_index()
            self.vaccine = VaccineResolver(self.mesh)

            EntityResolverJCDL.__instance = self

    @staticmethod
    def instance() -> EntityResolverJCDL:
        if EntityResolverJCDL.__instance is None:
            EntityResolverJCDL()
        return EntityResolverJCDL.__instance

    def get_name_for_var_ent_id(self, entity_id):
        """
        Translates an entity id and type to its name
        :param entity_id: the entity id
        :return: uses the corresponding resolver for the entity type
        """
        if entity_id.startswith('CHEMBL'):
            return self.chebml.chemblid_to_name(entity_id)
        if entity_id.startswith('FIDXLM1'):
            return "Assay"
        if entity_id.startswith('MESH:'):
            return self.mesh.descriptor_to_heading(entity_id)
        try:
            return self.species.species_id_to_name(entity_id)
        except KeyError:
            pass

        try:
            return self.dosageform.dosage_form_to_name(entity_id)
        except KeyError:
            pass
        try:
            return self.vaccine.vaccine_to_heading(entity_id)
        except KeyError:
            pass
        try:
            return self.gene.gene_locus_to_description(entity_id)
        except KeyError:
            pass

        return entity_id
