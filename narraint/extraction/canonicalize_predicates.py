import argparse
import logging
import fasttext
from datetime import datetime
from sqlalchemy import update
from scipy.spatial.distance import cosine

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.extraction.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.engine import QueryEngine
from narraint.progress import print_progress_with_eta

PRED_TO_REMOVE = "REMOVE"


def match_predicates(model, predicates: [str], vocab_predicates: {str: [str]}):
    """
    The distance between each predicate and all predicates of the vocabulary are computed. The predicate is assigned
    to the closed predicate in the room. Cosine Similarity is used.
    :param model: fasttext Word Embedding
    :param predicates: a list of predicates
    :param vocab_predicates: the vocabulary as a dict mapping predicates to their synonyms
    :return: a dict mapping each predicate to a predicate of the vocabulary and a distance
    """
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


def canonicalize_predicates(best_matches: {str: (str, float)}):
    """
    Canonicalizes Predicates by resolving synonymous predicates. This procedure updates the database
    :param best_matches: dictionary which maps a predicate to a canonicalized predicate and a distance score
    :return: None
    """
    session = Session.get()
    start_time = datetime.now()
    i = 0
    for pred, (pred_canonicalized, _) in best_matches.items():
        if pred and pred_canonicalized != PRED_TO_REMOVE:
            stmt = update(Predication).where(Predication.predicate_cleaned == pred).\
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
