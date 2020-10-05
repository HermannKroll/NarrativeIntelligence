from narraint.analysis.cikm2020.search.strategy import KeywordStrategy, KeywordDistanceStrategy
from narraint.analysis.cikm2020.expert_evaluation import *
import logging


def test_keyword_perform_search():
    strat = KeywordStrategy("../../resources/textstrategy_files")
    prec, rec, fval = strat.perform_search(eval_q1, "PubMed", eval_q1_ids_met_dia, eval_q1_ids_correct)
    logging.info(f"{prec}/{rec}/{fval}")
    assert prec*rec > 0

def test_keyword_distance_perform_search():
    results = dict()
    for distance in range(0, 5000, 50):
        strat = KeywordDistanceStrategy("../../resources/textstrategy_files",distance)
        results[distance] = strat.perform_search(eval_q1, "PubMed", eval_q1_ids_met_dia, eval_q1_ids_correct)
    logging.info(results)

