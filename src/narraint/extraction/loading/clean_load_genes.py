import logging
from collections import namedtuple
from datetime import datetime
from typing import List


from narrant.entity.entityresolver import GeneResolver
from narrant.preprocessing.enttypes import GENE
from narrant.progress import print_progress_with_eta

PRED = namedtuple('Predication', ['doc_id', 'subj', 'pred', 'pred_cleaned', 'obj', 'conf', 'sent', 's_id', 's_str',
                                  's_type', 'o_id', 'o_str', 'o_type'])


def clean_and_translate_gene_ids(predications: List[PRED]):
    """
     Some extractions may contain several gene ids (these gene ids are encoded as "id1;id2;id3" as tags)
     This method splits these extraction in single facts with only a single gene id for each
     Gene IDs are unique for each species - We are only interested in the names of genes
     Thus, we map each gene id to its gene symbol, so that, e.g. CYP3A4 is the unique description for all species
     :param predications: a list of predications
     :return: a list of cleaned predications
     """
    logging.info('Cleaning and translating gene ids...')
    predications_cleaned = []
    generesolver = GeneResolver()
    generesolver.load_index()
    start_time = datetime.now()
    predications_len = len(predications)
    for idx, p in enumerate(predications):
        subj_ids = set()
        if p.s_type == GENE:
            if ';' in p.s_id:
                for g_id in p.s_id.split(';'):
                    try:
                        subj_ids.add(generesolver.gene_id_to_symbol(g_id).lower())
                    except (KeyError, ValueError):
                        continue
            else:
                try:
                    subj_ids.add(generesolver.gene_id_to_symbol(p.s_id).lower())
                except (KeyError, ValueError):
                    continue
        else:
            subj_ids = [p.s_id]
        obj_ids = set()
        if p.o_type == GENE:
            if ';' in p.o_id:
                for g_id in p.o_id.split(';'):
                    try:
                        obj_ids.add(generesolver.gene_id_to_symbol(g_id).lower())
                    except (KeyError, ValueError):
                        continue
            else:
                try:
                    obj_ids.add(generesolver.gene_id_to_symbol(p.o_id).lower())
                except (KeyError, ValueError):
                    continue
        else:
            obj_ids = [p.o_id]
        for s_id in subj_ids:
            for o_id in obj_ids:
                p_cleaned = PRED(p.doc_id, p.subj, p.pred, p.pred_cleaned, p.obj, p.conf, p.sent, s_id, p.s_str,
                                 p.s_type, o_id, p.o_str, p.o_type)
                predications_cleaned.append(p_cleaned)
        print_progress_with_eta('cleaning gene ids...', idx, predications_len, start_time)
    logging.info('{} predications obtained'.format(len(predications_cleaned)))
    return predications_cleaned
