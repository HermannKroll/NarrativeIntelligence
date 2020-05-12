import argparse
import logging

from narraint.analysis.cikm2020.helper import retrieve_subdescriptors
from narraint.analysis.cikm2020.mesh_evaluation import pubmed_mesh_hits, perform_evaluation
from narraint.entity.enttypes import DISEASE, CHEMICAL
from narraint.entity.meshontology import MeSHOntology
from narraint.opendependencyextraction.main import PATH_EXTRACTION
from narraint.openie.main import OPENIE_EXTRACTION
from narraint.queryengine.engine import QueryEngine
from ui.views import convert_query_text_to_fact_patterns

queries_pubmed = []

eval_q1 = "Metformin treats \"Diabetes Mellitus\""
eval_q1_ids_met_dia = {25817734, 25742316, 26982095, 7484707, 30583483, 8778506, 20413862, 17697057, 21506631, 16503761, 24950434, 21733056, 20663465, 21465524, 29990880, 23207880, 24482374, 23795975, 23557845, 27108145, 24075453, 31300570, 27155828, 19337532, 24118860}
eval_q1_ids_correct = {25817734, 25742316, 26982095, 7484707, 30583483}
queries_pubmed.append((eval_q1, eval_q1_ids_met_dia, eval_q1_ids_correct))


eval_q2 = "Simvastatin decreases Cholesterol"
eval_q2_ids_sim_chol = {15856040, 12860491, 29361285, 8538379, 25637322, 9834769, 25676434, 19332196, 8775473, 10484079, 24283488, 19504041, 21906051, 10907971, 15571484, 29643243, 16272695, 20564244, 12885745, 26273214, 12549983, 11912560, 24740652, 2304688, 17398372}
eval_q2_ids_correct = {}
#queries_pubmed.append((eval_q2, eval_q2_ids_sim_chol, eval_q2_ids_correct))

eval_q3 = "Simvastatin causes Rhabdomyolysis"
eval_q3_ids_sim_rab = {12131698, 27750346, 23444397, 16098846, 23782756, 19778232, 15285699, 11550401, 24283488, 29189310, 26106178, 14558433, 29799296, 11977859, 10627888, 18650173, 17044581, 26134595, 18175291, 12495360, 21291776, 17368833, 11583063, 24327265, 21446776}
eval_q3_ids_correct = {12131698, 23444397, 16098846, 11550401, 24283488, 29189310}
queries_pubmed.append((eval_q3, eval_q3_ids_sim_rab, eval_q3_ids_correct))

eval_q4 = "Metformin inhibits Gene:2475"
eval_q4_ids_met_mtor = {26760500, 29253574, 22427958, 31186373, 30259865, 20305377, 27803295, 22611195, 30515768, 26756023, 24505341, 28242651, 30886744, 21540236, 27264609, 26967226, 29694764, 27796611, 23526220, 21631893, 24437490, 26304716, 30989649, 28168653, 23701880}
eval_q4_ids_correct = {}
#queries_pubmed.append((eval_q4, eval_q4_ids_met_mtor, eval_q4_ids_correct))


eval_q5_ids_pmc_sim_cyp_ery = {}
eval_q5_ids_correct = {}

eval_q6_ids_pmc_sim_cyp_ami = {}
eval_q6_ids_correct = {}

query_engine = QueryEngine()



def perform_baseline_evaluation(subject_id, predicate, object_id, ids_sample, ids_correct):
    pubmed_hits = pubmed_mesh_hits(subject_id, predicate, object_id, compute_subdescriptors=True)
    pubmed_hits_sample = len(pubmed_hits.intersection(ids_sample))
    pubmed_correct_hits = len(pubmed_hits.intersection(ids_correct))
    if pubmed_hits_sample:
        precision = pubmed_correct_hits / pubmed_hits_sample
        recall = pubmed_correct_hits / len(ids_correct)
    else:
        precision = 0
        recall = 0
    return precision, recall, len(pubmed_hits), pubmed_hits_sample, pubmed_correct_hits



def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument("output", help='resulting file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info('Beginning experiment...')
    logging.info('=' * 60)
    for query, id_sample, ids_correct in queries_pubmed:
        logging.info('=' * 60)
        logging.info('Query: {}'.format(query))
        query_fact_patterns, query_trans = convert_query_text_to_fact_patterns(query)
        logging.info('-' * 60)
        logging.info('Baseline')
        subject_id = query_fact_patterns[0][0]
        predicate = query_fact_patterns[0][2]
        object_id = query_fact_patterns[0][3]
        precision, recall, len_doc_ids, len_ids_in_sample, len_correct = perform_baseline_evaluation(subject_id, predicate, object_id, id_sample, ids_correct)
        logging.info(
            '{} retrieved, {} ids found in sample, {} ids are correct'.format(len_doc_ids, len_ids_in_sample,
                                                                              len_correct))
        logging.info('Precision: {}'.format(precision))
        logging.info('Recall: {}'.format(recall))
        logging.info('-' * 60)
        logging.info('-' * 60)
        logging.info("OpenIE")
        precision, recall, len_doc_ids, len_ids_in_sample, len_correct = perform_evaluation(query_engine,
                                                                                            query_fact_patterns,
                                                                                            "PubMed", OPENIE_EXTRACTION,
                                                                                            ids_correct,id_sample=id_sample,
                                                                                            do_expansion=True)
        logging.info(
            '{} retrieved, {} ids found in sample, {} ids are correct'.format(len_doc_ids, len_ids_in_sample, len_correct))
        logging.info('Precision: {}'.format(precision))
        logging.info('Recall: {}'.format(recall))

        logging.info('-' * 60)
        logging.info("PathIE")
        precision, recall, len_doc_ids, len_ids_in_sample, len_correct = perform_evaluation(query_engine,
                                                                                            query_fact_patterns,
                                                                                            "PubMed", PATH_EXTRACTION,
                                                                                            ids_correct, id_sample=id_sample,
                                                                                            do_expansion=True)
        logging.info(
            '{} retrieved, {} ids found in sample, {} ids are correct'.format(len_doc_ids, len_ids_in_sample, len_correct))
        logging.info('Precision: {}'.format(precision))
        logging.info('Recall: {}'.format(recall))
        logging.info('='*60)
    logging.info('=' * 60)


if __name__ == "__main__":
    main()