import argparse
import logging
import fasttext
from datetime import datetime
from sqlalchemy import update
from scipy.spatial.distance import cosine

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.openie.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.engine import QueryEngine
from narraint.progress import print_progress_with_eta

PRED_TO_REMOVE = "BIN_PREDICATE"


#def create_predicate_vocab_umls():
#    pred_vocab = ["ADMINISTERED_TO", "AFFECTS", "ASSOCIATED_WITH", "AUGMENTS", "CAUSES", "COEXISTS_WITH", "COMPLICATES",
#                  "CONVERTS_TO", "DIAGNOSES", "DISRUPTS", "INHIBITS", "INTERACTS_WITH", "ISA", "LOCATION_OF",
#                  "MANIFESTATION_OF", "METHOD_OF", "NEG_ADMINISTERED_TO", "NEG_AFFECTS", "NEG_ASSOCIATED_WITH",
#                  "NEG_AUGMENTS", "NEG_CAUSES", "NEG_COEXISTS_WITH", "NEG_COMPLICATES", "NEG_CONVERTS_TO",
#                  "NEG_DIAGNOSES", "NEG_DISRUPTS", "NEG_INHIBITS", "NEG_INTERACTS_WITH", "NEG_LOCATION_OF",
#                  "NEG_MANIFESTATION_OF", "NEG_METHOD_OF", "NEG_OCCURS_IN", "NEG_PART_OF", "NEG_PRECEDES",
#                  "NEG_PREDISPOSES", "NEG_PREVENTS", "NEG_PROCESS_OF", "NEG_PRODUCES", "NEG_STIMULATES", "NEG_TREATS",
#                  "NEG_USES", "NEG_higher_than", "NEG_lower_than", "OCCURS_IN", "PART_OF", "PRECEDES", "PREDISPOSES",
#                  "PREVENTS", "PROCESS_OF", "PRODUCES", "STIMULATES", "TREATS", "USES", "compared_with",
#                  "different_from", "higher_than", "lower_than", "same_as"]
#
#    pred_vocab_cleaned = []
#    for gp in pred_vocab:
#        if 'NEG' in gp:
#            continue
#        pred_vocab_cleaned.append(gp.lower().replace('_', ' '))
#    return pred_vocab_cleaned


def match_predicates(model, predicates, vocab_predicates):
    vocab_vectors = []
    for k, v_preds in vocab_predicates.items():
        for v_p in v_preds:
            vocab_vectors.append((k, model.get_word_vector(v_p)))

    start_time = datetime.now()
    best_matches = {}
    i = 0
    task_size = len(predicates) * len(vocab_vectors)
    for p in predicates:
        vec = model.get_word_vector(p)
        best_match = None
        min_distance = 1.0
        for p_v_idx, (p_can_v, p_v) in enumerate(vocab_vectors):
            current_distance = cosine(vec, p_v)
            if not best_match or current_distance < min_distance:
                min_distance = current_distance
                best_match = (p_can_v, min_distance)

            print_progress_with_eta('computing distances...', i, task_size, start_time)
            i += 1

        if p in best_matches:
            raise ValueError('p should not be twice in predicates (duplicate found)')
        best_matches[p] = (best_match[0], best_match[1])

    return best_matches


def canonicalize_predicates(best_matches):
    session = Session.get()

    start_time = datetime.now()
    i = 0
    for pred, (pred_canonicalized, _) in best_matches.items():
        if pred and pred_canonicalized != PRED_TO_REMOVE:
            stmt = update(Predication).where(Predication.predicate_cleaned == pred). \
                values(predicate_canonicalized=pred_canonicalized)
        else:
            stmt = update(Predication).where(Predication.predicate_cleaned == pred). \
                values(predicate_canonicalized=None)

        session.execute(stmt)
        session.commit()
        print_progress_with_eta('updating...', i, len(best_matches), start_time, print_every_k=5)
        i += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("word2vec_model", help='word2vec file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Loading Word2Vec model...')
    model = fasttext.load_model(args.word2vec_model)
    logging.info('Creating predicate vocabulary...')
    pred_vocab = create_predicate_vocab()
    logging.info('{} predicates in vocabulary'.format(len(pred_vocab)))
    logging.info('Retrieving predicates from db...')
    predicates = QueryEngine.query_predicates_cleaned()
    logging.info('{} predicates retrieved'.format(len(predicates)))
    logging.info('Matching predicates...')
    best_matches = match_predicates(model, predicates, pred_vocab)
    logging.info('Canonicalizing predicates...')
    canonicalize_predicates(best_matches)


if __name__ == "__main__":
    main()
