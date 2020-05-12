import argparse
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func

from narraint.analysis.cikm2020.helper import retrieve_subdescriptors, perform_evaluation
from narraint.analysis.pubmed_medline import PubMedMEDLINE
from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.entity.enttypes import DISEASE, CHEMICAL, GENE
from narraint.opendependencyextraction.main import PATH_EXTRACTION
from narraint.openie.main import OPENIE_EXTRACTION
from narraint.progress import print_progress_with_eta
from narraint.queryengine.engine import QueryEngine

# See list of subheadings: https://www.ncbi.nlm.nih.gov/books/NBK3827/table/pubmedhelp.T.mesh_subheadings/
# More information: https://wayback.archive-it.org/org-350/20191102205211/https://www.nlm.nih.gov/mesh/topsubscope.html



# Analyse treats, decreases, causes, inhibits and induces

# Treats:
# Therapy: D004358 https://www.ncbi.nlm.nih.gov/mesh/68004358
# Qualifiers:
# Q000008: administration and dosage https://meshb.nlm.nih.gov/record/ui?ui=Q000008
# Q000627: therapeutic usage https://meshb.nlm.nih.gov/record/ui?ui=Q000627
treats_subject_qualifiers = ['Q000008', 'Q000627']
# Q000628 therapy: https://www.ncbi.nlm.nih.gov/mesh/81000628
treats_object_qualifiers = ['Q000628']
treats_additional_descriptors = ['D004358']
treats_enhanced_search = (treats_subject_qualifiers, treats_object_qualifiers, treats_additional_descriptors)


# Causes:
# Q000009: adverse effects https://meshb.nlm.nih.gov/record/ui?ui=Q000009
causes_subject_qualifiers = ['Q000009']
# Q000139: chemically induced https://meshb.nlm.nih.gov/record/ui?ui=Q000139
causes_object_qualifiers = ['Q000139']
# D064420 Drug-Related Side Effects and Adverse Reactions https://meshb.nlm.nih.gov/record/ui?ui=D064420
causes_additional_descriptors = ['D064420']
causes_enhanced_search = (causes_subject_qualifiers, causes_object_qualifiers, causes_additional_descriptors)


# Inhibits:
# for drugs
# Q000037: antagonists & inhibitors https://meshb.nlm.nih.gov/record/ui?ui=Q000037
inhibits_subject_qualifiers = ['Q000037']
# for genes
# Q000378: metabolism https://meshb.nlm.nih.gov/record/ui?ui=Q000378
inhibits_object_qualifiers = ['Q000378']
# Cytochrome P-450 CYP3A Inhibitors https://www.ncbi.nlm.nih.gov/mesh/68065692
inhibits_additional_descriptors = ['D065692']
inhibits_enhanced_search = (inhibits_subject_qualifiers, inhibits_object_qualifiers, inhibits_additional_descriptors)

# Induces:
# Q000378: metabolism https://meshb.nlm.nih.gov/record/ui?ui=Q000378
induces_subject_qualifiers = ['Q000378']
induces_object_qualifiers = []
induces_additional_descriptors = []
induces_enhanced_search = (induces_subject_qualifiers, induces_object_qualifiers, induces_additional_descriptors)


# Decreases:
#
decreases_subject_qualifiers = []
decreases_object_qualifiers = []
decreases_additional_descriptors = []
decreases_enhanced_search = (decreases_subject_qualifiers, decreases_object_qualifiers, decreases_additional_descriptors)

terms_for_relation = dict(treats=treats_enhanced_search, causes=causes_enhanced_search,
                          inhibits=inhibits_enhanced_search, induces=induces_enhanced_search)

#query_predicates =  [("treats" , [CHEMICAL] , [DISEASE]), ("causes", [CHEMICAL], [DISEASE])]
#query_predicates =  [("treats" , [CHEMICAL] , [DISEASE])]
#query_predicates = [("inhibits", [CHEMICAL], [GENE])]
query_predicates = [("induces", [GENE], [CHEMICAL])]


query_engine = QueryEngine()
session = Session.get()
pubmed = PubMedMEDLINE()

GENE_NCBI_TO_MESH_MAPPING = {"1576": 'MESH:D051544' }
GENE_MESH_TO_NCBI = {v: k for k,v in GENE_NCBI_TO_MESH_MAPPING.items()}

def compute_mesh_queries(sub_id, obj_id, predicate):
    sub_qualifiers, obj_qualifiers, add_mesh_descs = terms_for_relation[predicate]
    queries = []

    # subject + qualifier and object
    for sub_q in sub_qualifiers:
        s_t = '{}_{}'.format(sub_id, sub_q)
        queries.append([s_t, obj_id])
    # subject and object + qualifier
    for obj_q in obj_qualifiers:
        o_t = '{}_{}'.format(obj_id, obj_q)
        queries.append([sub_id, o_t])
    # combination of all qualifiers
    for sub_q in sub_qualifiers:
        s_t = '{}_{}'.format(sub_id, sub_q)
        for obj_q in obj_qualifiers:
            o_t = '{}_{}'.format(obj_id, obj_q)
            queries.append([s_t, o_t])
    # object and subject + each additional desc
    for mesh_desc in add_mesh_descs:
        queries.append([sub_id, obj_id, mesh_desc])
    return queries


def pubmed_mesh_hits(sub_id, predicate, obj_id, compute_subdescriptors=True):
    if not sub_id.startswith('MESH:') or not obj_id.startswith('MESH:'):
        raise ValueError('does not support mesh search without suitable Descriptors')
    doc_ids = set()
    sub_without_mesh = sub_id.replace('MESH:', '')
    obj_without_mesh = obj_id.replace('MESH:', '')
    if compute_subdescriptors:
        subj_sub_descriptors = retrieve_subdescriptors(sub_without_mesh)
        obj_sub_descriptors = retrieve_subdescriptors(obj_without_mesh)
        for subj_desc, _ in subj_sub_descriptors:
            for obj_desc, _ in obj_sub_descriptors:
                for q_descs in compute_mesh_queries(subj_desc, obj_desc, predicate):
                    doc_ids.update(pubmed.get_ids(q_descs))
    else:
        for q_descs in compute_mesh_queries(sub_without_mesh, obj_without_mesh, predicate):
            doc_ids.update(pubmed.get_ids(q_descs))
    return doc_ids




def get_subject_object_for_predicate(predicate, extraction_type, subject_types=None, object_types=None):
    query = session.query(Predication.document_id, Predication.subject_id, Predication.subject_type,
                          Predication.object_id, Predication.object_type)\
        .filter_by(predicate_canonicalized=predicate)\
        .filter_by(document_collection='PubMed')\
        .filter_by(extraction_type=extraction_type)
    if subject_types:
        query = query.filter(Predication.subject_type.in_(subject_types))
    if object_types:
        query = query.filter(Predication.object_type.in_(object_types))
#    query = query.group_by(Predication.subject_id, Predication.subject_type,
#                           Predication.object_id, Predication.object_type)
#    query = query.having(func.count() > 2)

    results = defaultdict(set)
    for row in session.execute(query):
        doc_id, sub_id, sub_type, obj_id, obj_type = row
        if obj_type == GENE:
            # remap gene id to mesh descriptor
            if obj_id in GENE_NCBI_TO_MESH_MAPPING:
                obj_id = GENE_NCBI_TO_MESH_MAPPING[obj_id]
            else:
                continue
        if sub_type == GENE:
            if sub_id in GENE_NCBI_TO_MESH_MAPPING:
                sub_id = GENE_NCBI_TO_MESH_MAPPING[sub_id]
            else:
                continue
        if not sub_id.startswith('MESH:D') or not obj_id.startswith('MESH:D'):
            continue
        key = (sub_id, sub_type, obj_id, obj_type)
        results[key].add(doc_id)

    result_set = set()
    for key, doc_ids in results.items():
        if len(doc_ids) > 2:
            sub_id, sub_type, obj_id, obj_type = key
            result_set.add((sub_id, sub_type, obj_id, obj_type))
    return result_set


def perform_evaluation_prec_recall_for(query_fact_patterns, document_collection, extraction_type, ids_correct):
    query_results = query_engine.query_with_graph_query(query_fact_patterns, document_collection, extraction_type)
    doc_ids = set([q_r.document_id for q_r in query_results])
    doc_ids_correct = doc_ids.intersection(ids_correct)
    len_retrieved = len(doc_ids)
    len_retrieved_correct = len(doc_ids_correct)
    len_correct = len(ids_correct)
    # no correct hits?
    if not len_correct:
        return len_retrieved, 0.0, 0.0
    if len_retrieved:
        precision = len_retrieved_correct / len_retrieved
        recall = len_retrieved_correct / len_correct
    else:
        raise ValueError('each query should return at least one result: {}'.format(query_fact_patterns))
    return len_retrieved, precision, recall



def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument("output", help='resulting file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)


    logging.info('Beginning experiment...')
    logging.info('=' * 60)
    for DO_QUERY_MESH_EXPANSION in [True, False]:
        logging.info('Query expansion set to: {}'.format(DO_QUERY_MESH_EXPANSION))
        for p, p_s_types, p_o_types in query_predicates:
            logging.info('=' * 60)
            for extraction_type in [OPENIE_EXTRACTION, PATH_EXTRACTION]:
                if DO_QUERY_MESH_EXPANSION:
                    filename = 'eval_mesh_{}_{}_expansion.tsv'.format(extraction_type, p)
                else:
                    filename = 'eval_mesh_{}_{}.tsv'.format(extraction_type, p)

                with open(filename, 'wt') as f:
                    f.write('subject_id\tobject_id\thits_pubmed\thits_graph\tprecision\trecall')
                    logging.info('-' * 60)
                    logging.info('{}'.format(extraction_type))
                    logging.info('Query subjects and objects for predicate: {} ({} -> {})'.format(p, p_s_types, p_o_types))
                    pred_subjects_and_objects = get_subject_object_for_predicate(p, extraction_type, p_s_types, p_o_types)
                    logging.info('{} subject-object pairs retrieved'.format(len(pred_subjects_and_objects)))
                    start_time = datetime.now()
                    task_size = len(pred_subjects_and_objects)

                    l_hits = []
                    l_precision = []
                    l_recall = []
                    status_outout = 'checking {} ({})'.format(p, extraction_type)
                    for idx, (sub_id, sub_type, obj_id, obj_type) in enumerate(pred_subjects_and_objects):
                        ids_correct = pubmed_mesh_hits(sub_id, p, obj_id, compute_subdescriptors=DO_QUERY_MESH_EXPANSION)
                        if obj_type == GENE:
                            obj_id = GENE_MESH_TO_NCBI[obj_id]
                        if sub_type == GENE:
                            sub_id = GENE_MESH_TO_NCBI[sub_id]
                        query_fact_patterns = [(sub_id, sub_type, p, obj_id, obj_type)]
                        precision, recall, hits, _, _ = perform_evaluation(query_engine, query_fact_patterns,
                                                                                     "PubMed", extraction_type,
                                                                                     ids_correct,
                                                                           do_expansion=DO_QUERY_MESH_EXPANSION)
                        line_to_write = '\n{}\t{}\t{}\t{}\t{}\t{}'.format(sub_id, obj_id, len(ids_correct), hits, precision, recall)
                        f.write(line_to_write)
                        l_hits.append((hits, ids_correct))
                        l_precision.append(precision)
                        l_recall.append(recall)
                        #logging.info('{} PubMed Hits, {} Graph Hits, Prec: {} , Recall: {}'.format(len(ids_correct), hits,
                         #                                                                          precision, recall))
                        print_progress_with_eta(status_outout, idx, task_size, start_time, print_every_k=1)

                logging.info('-' * 60)
            logging.info('=' * 60)
    logging.info('=' * 60)


if __name__ == "__main__":
    main()