import logging

from narraint.analysis.pubmed_medline import PubMedMEDLINE
from narraint.entity.meshontology import MeSHOntology
from narraint.semmeddb.dbconnection import SemMedDB



def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    query = """
    SELECT DISTINCT P1.subject_cui, P2.object_cui
    FROM Predication P1, Predication P2
    WHERE P1.object_cui = 'C1142644|1576' AND P1.predicate = 'INHIBITS'
    AND (P1.subject_semtype = 'clnd' OR P1.subject_semtype = 'phsu' OR P1.subject_semtype = 'sbst')
    AND P2.subject_cui = 'C1142644|1576' AND P2.predicate = 'INTERACTS_WITH'
    AND (P2.object_semtype = 'clnd' OR P2.object_semtype = 'phsu' OR P2.object_semtype = 'sbst')
    """
    logging.info('Loading PubMed index')
    pubmed = PubMedMEDLINE()
    logging.info('Creating reverse index')
    pubmed.create_reverse_index()
    logging.info('Finished')
    logging.info('Loading MeSH Ontology')
    mesh_ontology = MeSHOntology()
    logging.info('Finished')

    semmed = SemMedDB()
    semmed.load_umls_dictionary()
    semmed.connect_to_db()
    rows, time = semmed.execute_select_query(query)
    logging.info('{} results computed by semmeddb'.format(len(rows)))

    drugs = set()
    drug_combinations = set()
    for r in rows:
        drugs.add(r[0])
        drugs.add(r[1])
        drug_combinations.add((r[0], r[1]))

    logging.info('{} unique drugs'.format(len(drugs)))
    drug_cui2mesh = {}
    drug_mesh2cui = {}
    for d in drugs:
        try:
            drug_cui2mesh[d] = semmed.cui2mesh[d]
        except KeyError:
            pass
    logging.info('{} drugs can be translated to MeSH'.format(len(drug_cui2mesh)))
    translated_narratives = 0
    grounded = 0
    grounded_drug_combinations = set()
    grounded_drug_combination_with_disease = set()
    for d_inhibits, d_metabol in drug_combinations:
        if d_inhibits not in drug_cui2mesh or d_metabol not in drug_cui2mesh:
            continue
        translated_narratives += 1
        d_inhibits_mesh = drug_cui2mesh[d_inhibits]
        d_metabol_mesh = drug_cui2mesh[d_metabol]
        gene_desc = 'D051544'

        # Q000378: metabolism https://meshb.nlm.nih.gov/record/ui?ui=Q000378
        d_metabol_accumulation = d_metabol_mesh + '_Q000378'

        # Q000009: adverse effects https://meshb.nlm.nih.gov/record/ui?ui=Q000009
        d_metabol_adverse_effect = d_metabol_mesh + '_Q000009'

        pubmed_query = [d_inhibits_mesh, d_metabol_mesh, gene_desc]#, d_metabol_accumulation, d_metabol_adverse_effect]
        pmids = pubmed.get_ids(pubmed_query)
        if len(pmids) > 0:
            for pmid in pmids:
                descs = pubmed.pmid_to_descs[pmid]
                for desc in descs:
                    for tn in mesh_ontology.get_tree_numbers_for_descriptor(desc):
                        if tn.startswith('C'):
                            # it's a disease
                            grounded_drug_combination_with_disease.add((d_inhibits_mesh, d_metabol_mesh, desc))

            # Todo: Get Descriptors for each ids and build a distinct set of diseases
            #logging.info('{} documents found'.format(len(pmids)))
            grounded_drug_combinations.add((d_inhibits_mesh, d_metabol_mesh))
            grounded += 1
    logging.info('{} of {} narratives can be grounded'.format(grounded, translated_narratives))
    logging.info('{} narratives obtained with disease'.format(len(grounded_drug_combination_with_disease)))
    #
    # logging.info('obtaining correct drug-drug interactions from semmedb')
    # ddi_query = """SELECT DISTINCT d1, drug2 FROM mv_ddi_correct"""
    # ddi_rows, _ = semmed.execute_select_query(ddi_query)
    # correct_ddis = set()
    # for row in ddi_rows:
    #     correct_ddis.add((row[0], row[1]))
    #
    # count_correct = 0
    # for d1, d2 in drug_combinations:
    #     if (d1, d2) in correct_ddis:
    #         count_correct += 1
    # logging.info('{} of {} drug interactions are correct'.format(count_correct, len(drug_combinations)))
    # count_correct = 0
    # for d1, d2 in grounded_drug_combinations:
    #     if (d1, d2) in correct_ddis:
    #         count_correct += 1
    # logging.info('{} of {} drug interactions are correct'.format(count_correct, len(grounded_drug_combinations)))


if __name__ == "__main__":
    main()