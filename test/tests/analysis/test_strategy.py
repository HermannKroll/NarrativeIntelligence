from narraint.analysis.cikm2020.search.strategy import KeywordStrategy
from narraint.analysis.cikm2020.expert_evaluation import eval_q1_ids_met_dia, eval_q1_ids_correct
import logging


def test_perform_search():
    strat = KeywordStrategy("../../resources/textstrategy_files")
    query = 'Metformin treats "Diabetes Mellitus"'
    prec, rec, fval = strat.perform_search(query, "PubMed", eval_q1_ids_met_dia, eval_q1_ids_correct)
    logging.info(f"{prec}/{rec}/{fval}")
    assert prec*rec > 0