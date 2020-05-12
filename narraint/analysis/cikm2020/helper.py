import logging

from narraint.entity.meshontology import MeSHOntology

mesh_ontology = MeSHOntology()


def retrieve_subdescriptors(decriptor_id: str) -> [(str, str)]:
    tree_nos = mesh_ontology.get_tree_numbers_for_descriptor(descriptor_id=decriptor_id)
    sub_descriptors = set()
    for t_n in tree_nos:
        for res in mesh_ontology.find_descriptors_start_with_tree_no(t_n):
            sub_descriptors.add(res)
    return sub_descriptors


def perform_evaluation(query_engine, query_fact_patterns, document_collection, extraction_type,
                                            ids_correct, id_sample=None, do_expansion=False, print_expansion=False):
    object_id = query_fact_patterns[0][3]
    object_type = query_fact_patterns[0][4]
    doc_ids = set()
    if do_expansion and object_type == 'MESH':
        if print_expansion:
            logging.info('Expanding query for object: {}'.format(object_id))
        obj_id_without_mesh = object_id.replace('MESH:', '')
        sub_descriptors = retrieve_subdescriptors(obj_id_without_mesh)
        if print_expansion:
            logging.info('Expand Query by: {}'.format(sub_descriptors))
        sub_id = query_fact_patterns[0][0]
        sub_type = query_fact_patterns[0][1]
        pred = query_fact_patterns[0][2]
        for d_id, d_head in sub_descriptors:
            expaned_obj_id = 'MESH:{}'.format(d_id)
            query_fact_patterns_new = [(sub_id, sub_type, pred, expaned_obj_id, object_type)]
            query_results = query_engine.query_with_graph_query(query_fact_patterns_new, document_collection,
                                                                extraction_type)
            retrieved_ids = set([q_r.document_id for q_r in query_results])
            if print_expansion:
                logging.info('{} hits for descriptor: {}'.format(len(retrieved_ids), d_head))
            doc_ids.update(retrieved_ids)
    else:
        query_results = query_engine.query_with_graph_query(query_fact_patterns, document_collection, extraction_type)
        doc_ids = set([q_r.document_id for q_r in query_results])
    if id_sample:
        doc_hits = doc_ids.intersection(id_sample)
    else:
        doc_hits = doc_ids
    doc_ids_correct = doc_hits.intersection(ids_correct)
    len_hits = len(doc_hits)
    len_correct = len(doc_ids_correct)
    if doc_ids_correct:
        precision = len_correct / len_hits
        recall = len_correct / len(ids_correct)
    else:
        precision = 0.0
        recall = 0.0
    return precision, recall, len(doc_ids), len_hits, len_correct
