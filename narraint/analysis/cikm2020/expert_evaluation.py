import logging
import os

from narraint.analysis.cikm2020.experiment_config import EXP_TEXTS_DIRECTORY
from narraint.analysis.cikm2020.mesh_evaluation import pubmed_mesh_hits
from narraint.analysis.cikm2020.search.strategy import OpenIESearchStrategy, PathIESearchStrategy, \
    SentenceEntityCooccurrence, SentenceFactCooccurrence, OpenIECorefSearchStrategy
from narraint.analysis.pubmed_medline import PubMedMEDLINE, PMCIndex
from narraint.backend.export import export
from narraint.backend.exports.pmc_fulltext_export import export_pmc_fulltexts_with_tags

from narraint.entity import enttypes
from narraint.pubtator.split import split
from narraint.queryengine.engine import QueryEngine

queries_pubmed = []

eval_q1 = "Metformin treats \"Diabetes Mellitus\""
eval_q1_trans = [("MESH:D008687", 'treats', "MESH:D003920")]
eval_q1_ids_met_dia = {25817734, 25742316, 26982095, 7484707, 30583483, 8778506, 20413862, 17697057, 21506631, 16503761,
                       24950434, 21733056, 20663465, 21465524, 29990880, 23207880, 24482374, 23795975, 23557845,
                       27108145, 24075453, 31300570, 27155828, 19337532, 24118860}
eval_q1_ids_correct = {25817734, 25742316, 26982095, 7484707, 30583483, 8778506, 20413862, 21506631, 16503761, 24950434,
                       21465524, 29990880, 24482374, 23795975, 23557845, 27108145, 24075453, 27155828, 19337532}
print('Q1: {} correct of {} documents'.format(len(eval_q1_ids_correct), len(eval_q1_ids_met_dia)))
queries_pubmed.append(("PubMed", eval_q1, eval_q1_trans, eval_q1_ids_met_dia, eval_q1_ids_correct))

eval_q2 = "Simvastatin decreases Cholesterol"
eval_q2_trans = [('MESH:D019821', 'decreases', 'MESH:D002784')]
eval_q2_ids_sim_chol = {15856040, 12860491, 29361285, 8538379, 25637322, 9834769, 25676434, 19332196, 8775473, 10484079,
                        24283488, 19504041, 21906051, 10907971, 15571484, 29643243, 16272695, 20564244, 12885745,
                        26273214, 12549983, 11912560, 24740652, 2304688, 17398372}
eval_q2_ids_correct = {15856040, 12860491, 8538379, 25676434, 8775473, 10484079, 24283488, 19504041, 10907971, 15571484,
                       20564244, 12885745, 12549983, 24740652, 2304688, 17398372}
print('Q2: {} correct of {} documents'.format(len(eval_q2_ids_correct), len(eval_q2_ids_sim_chol)))
queries_pubmed.append(("PubMed", eval_q2, eval_q2_trans, eval_q2_ids_sim_chol, eval_q2_ids_correct))

eval_q3 = "Simvastatin induces Rhabdomyolysis"
eval_q3_trans = [('MESH:D019821', 'induces', 'MESH:D012206')]
eval_q3_ids_sim_rab = {12131698, 27750346, 23444397, 16098846, 23782756, 19778232, 15285699, 11550401, 24283488,
                       29189310, 26106178, 14558433, 29799296, 11977859, 10627888, 18650173, 17044581, 26134595,
                       18175291, 12495360, 21291776, 17368833, 11583063, 24327265, 21446776}
eval_q3_ids_correct = {12131698, 23444397, 16098846, 11550401, 24283488, 29189310, 26106178, 14558433, 29799296,
                       11977859, 10627888, 18650173, 17044581, 26134595, 18175291, 12495360, 17368833}
print('Q3: {} correct of {} documents'.format(len(eval_q3_ids_correct), len(eval_q3_ids_sim_rab)))
queries_pubmed.append(("PubMed", eval_q3, eval_q3_trans, eval_q3_ids_sim_rab, eval_q3_ids_correct))

eval_q4 = "Metformin inhibits mtor"
eval_q4_trans = [("MESH:D008687", 'inhibits', 'MESH:D058570')]
eval_q4_ids_met_mtor = {26760500, 29253574, 22427958, 31186373, 30259865, 20305377, 27803295, 22611195, 30515768,
                        26756023, 24505341, 28242651, 30886744, 21540236, 27264609, 26967226, 29694764, 27796611,
                        23526220, 21631893, 24437490, 26304716, 30989649, 28168653, 23701880}
eval_q4_ids_correct = {26760500, 29253574, 20305377, 27803295, 22611195, 30515768, 24505341, 28242651, 30886744,
                       21540236, 27264609, 26967226, 29694764, 24437490, 30989649, 28168653}
print('Q4: {} correct of {} documents'.format(len(eval_q4_ids_correct), len(eval_q4_ids_met_mtor)))
queries_pubmed.append(("PubMed", eval_q4, eval_q4_trans, eval_q4_ids_met_mtor, eval_q4_ids_correct))

# PMC
# Erythromycin: D004917
eval_q5 = "Gene:1576 metabolises Simvastatin. MESH:D004917 inhibits Gene:1576"
# MESH:D051544 = CYP3A4
eval_q5_trans = [('MESH:D051544', 'metabolises', 'MESH:D019821'), ('MESH:D004917', 'inhibits', 'MESH:D051544')]
eval_q5_ids_pmc_sim_cyp_ery = {28442937, 18360537, 30815270, 19436666, 26674520, 28144253, 22327313, 23585384, 20512335,
                               18225466, 25028555, 24474103, 30345053, 29950882, 27664109, 21577272, 16480505, 26089839,
                               14612892, 30808332, 24448021, 24888381, 23444277, 30092624, 25505582}
eval_q5_ids_correct = {28442937, 18360537, 30815270, 19436666, 26674520, 28144253}
print('Q5: {} correct of {} documents'.format(len(eval_q5_ids_correct), len(eval_q5_ids_pmc_sim_cyp_ery)))
queries_pubmed.append(("PMC", eval_q5, eval_q5_trans, eval_q5_ids_pmc_sim_cyp_ery, eval_q5_ids_correct))

# Amiodarone: D000638
eval_q6 = "Gene:1576 metabolises Simvastatin. MESH:D000638 inhibits Gene:1576"
eval_q6_trans = [('MESH:D051544', 'metabolises', 'MESH:D019821'), ('MESH:D000638', 'inhibits', 'MESH:D051544')]
eval_q6_ids_pmc_sim_cyp_ami = {30345053, 25883814, 27716084, 25861286, 24434254, 22084608, 24308359, 25505590, 20972517,
                               22096377, 30302080, 29067253, 28321163, 27538727, 25135287, 30526249, 29780235, 29361723,
                               29997136, 23700039, 28097103, 28442915, 26819251, 19436657, 23974980}
eval_q6_ids_correct = {30345053, 25883814, 27716084, 25861286, 24434254}
print('Q6: {} correct of {} documents'.format(len(eval_q6_ids_correct), len(eval_q6_ids_pmc_sim_cyp_ami)))
queries_pubmed.append(("PMC", eval_q6, eval_q6_trans, eval_q6_ids_pmc_sim_cyp_ami, eval_q6_ids_correct))

query_engine = QueryEngine()


def perform_baseline_evaluation(mesh_index, facts: [(str, str, str)], ids_sample,
                                ids_correct):
    """
    Baseline = PubMed MeSH Term search
    :param mesh_index: mesh index
    :param facts: a list of facts containing subject, predicate and object
    :param ids_sample: sample - which document were evaluated by the experts
    :param ids_correct: which documents are correct hits
    :return: precision, recall, len_hits_on_pubmed, len_hits_sample, len_hits_correct
    """
    pubmed_hits = set()
    for subject_id, predicate, object_id in facts:
        pubmed_hits.update(pubmed_mesh_hits(mesh_index, subject_id, predicate, object_id, compute_subdescriptors=True))
    pubmed_hits_sample = len(pubmed_hits.intersection(ids_sample))
    pubmed_correct_hits = len(pubmed_hits.intersection(ids_correct))
    if pubmed_hits_sample:
        precision = pubmed_correct_hits / pubmed_hits_sample
        recall = pubmed_correct_hits / len(ids_correct)
    else:
        precision = 0
        recall = 0
    return precision, recall, len(pubmed_hits), pubmed_hits_sample, pubmed_correct_hits


def export_document_texts(doc_ids, document_collection):
    if not os.path.isdir(EXP_TEXTS_DIRECTORY):
        os.makedirs(EXP_TEXTS_DIRECTORY)
    export_needed = False
    for doc_id in doc_ids:
        fn = os.path.join(EXP_TEXTS_DIRECTORY, '{}_{}.txt'.format(document_collection, doc_id))
        if not os.path.isfile(fn):
            export_needed = True
    if export_needed:
        temp_file = os.path.join(EXP_TEXTS_DIRECTORY, 'temp.pubtator')
        if document_collection == 'PubMed':
            export(temp_file, enttypes.ALL, doc_ids, document_collection, content=True)
        elif document_collection == 'PMC':
            export_pmc_fulltexts_with_tags(temp_file, enttypes.ALL, doc_ids)
        else:
            raise ValueError('Document collection is not supported: {}'.format(document_collection))
        split(temp_file, EXP_TEXTS_DIRECTORY, document_prefix='{}_'.format(document_collection))
        os.remove(temp_file)


def main():
    """
    performs the expert evaluation of CIKM2020
    :return:
    """
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info('loading indexes...')
    mesh_index_pubmed = PubMedMEDLINE()
    mesh_index_pmc = PMCIndex()
    doc_collection2mesh_index = {'PubMed': mesh_index_pubmed, 'PMC': mesh_index_pmc}
    logging.info('Beginning experiment...')
    logging.info('=' * 60)
    for document_collection, query, query_trans, ids_sample, ids_correct in queries_pubmed:
        logging.info('exporting document texts if missing...')
        export_document_texts(ids_sample, document_collection)
        logging.info('export finished')
        logging.info('=' * 60)
        logging.info('Query: {}'.format(query))
        logging.info('-' * 60)
        logging.info('Baseline')
        precision, recall, len_doc_ids, len_ids_in_sample, len_correct = perform_baseline_evaluation(
            doc_collection2mesh_index[document_collection],
            query_trans,
            ids_sample,
            ids_correct)
        logging.info(
            '{} retrieved, {} ids found in sample, {} ids are correct'.format(len_doc_ids, len_ids_in_sample,
                                                                              len_correct))
        logging.info('Precision: {}'.format(precision))
        logging.info('Recall: {}'.format(recall))
        if precision > 0.0 or recall > 0.0:
            f_score = 2 * (precision * recall) / (precision + recall)
            logging.info('F1-Score: {}'.format(f_score))

        evaluation_strategies = [OpenIESearchStrategy(query_engine), OpenIECorefSearchStrategy(query_engine)]
                                 #PathIESearchStrategy(query_engine),
                                 #SentenceEntityCooccurrence(), SentenceFactCooccurrence()]
        for strat in evaluation_strategies:
            logging.info('-' * 60)
            logging.info('-' * 60)
            logging.info('Performing strategy: {}'.format(strat.name))
            prec, rec, f1 = strat.perform_search(query, document_collection, ids_sample, ids_correct)
            logging.info('Precision: {}'.format(prec))
            logging.info('Recall: {}'.format(rec))
            logging.info('F1-Score: {}'.format(f1))
            logging.info('-' * 60)
            logging.info('-' * 60)

        logging.info('=' * 60)
    logging.info('=' * 60)


if __name__ == "__main__":
    main()
