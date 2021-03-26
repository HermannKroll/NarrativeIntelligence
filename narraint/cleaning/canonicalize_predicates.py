import argparse
import logging
from collections import defaultdict

import fasttext
from datetime import datetime
from sqlalchemy import update, and_
from scipy.spatial.distance import cosine

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.cleaning.predicate_vocabulary import create_predicate_vocab, PRED_TO_REMOVE
from narraint.progress import print_progress_with_eta


def transform_predicate(predicate: str):
    """
    Stems the predicate by two rules
    ends with s -> remove s
    ends with ed -> remove d
    :param predicate:
    :return:
    """
    if predicate.endswith('s'):
        return predicate[:-1]
    if predicate.endswith('ed'):
        return predicate[:-2]
    return predicate


def is_predicate_equal_to_vocab(predicate: str, vocab_term: str) -> bool:
    """
    fast regex check for vocab terms that starts or ends with a *
    Quickly checks, whether the predicate is a direct match to the vocab term
    :param predicate: the predicate
    :param vocab_term: a vocab term (may starting and/or ending with *)
    :return: true if both are equal
    """
    if vocab_term.startswith('*') and predicate.endswith(vocab_term[1:]):
        return True
    if vocab_term.endswith('*') and predicate.startswith(vocab_term[:-1]):
        return True
    if vocab_term.startswith('*') and vocab_term.endswith('*') and vocab_term[1:-1] in predicate:
        return True
    if vocab_term == predicate:
        return True
    return False


def filter_predicate_list(predicates_with_count, min_predicate_threshold):
    """
    Filters a list with predicates and counts by a minimum count threshold
    :param predicates_with_count: list of tuples (pred, count_of_pred)
    :param min_predicate_threshold: how often should a predicate occur at minimum (0.1 means that the predicate appears in at least 10% of all extractions)
    :return: a list of filtered predicates (pred_count >= min_predicate_threshold * all_count)
    """
    predicates = []
    pred_sum = sum([x[1] for x in predicates_with_count])
    min_count = int(min_predicate_threshold * pred_sum)
    logging.info(f'Minimum threshold for predicates is: {min_count}')
    for pred, count in predicates_with_count:
        if count >= min_count:
            predicates.append(pred)
    return predicates


def match_predicates(model, predicates: [str], vocab_predicates: {str: [str]}, output_file: str):
    """
    The distance between each predicate and all predicates of the vocabulary are computed. The predicate is assigned
    to the closed predicate in the room. Cosine Similarity is used.
    :param model: fasttext Word Embedding
    :param predicates: a list of predicates
    :param vocab_predicates: the vocabulary as a dict mapping predicates to their synonyms
    :param output_file: predicate distances will be exported to that file
    :return: a dict mapping each predicate to a predicate of the vocabulary and a distance
    """

    with open(output_file, 'wt') as f:
        vocab_vectors = []
        for goal_relation, v_preds in vocab_predicates.items():
            k_os = goal_relation.replace('*', '')
            vocab_vectors.append((goal_relation, transform_predicate(goal_relation),
                                  model.get_word_vector(transform_predicate(k_os))))
            for v_p in v_preds:
                v_p_os = v_p.replace('*', '')
                vocab_vectors.append((goal_relation, transform_predicate(v_p),
                                      model.get_word_vector(transform_predicate(v_p_os))))

        start_time = datetime.now()
        best_matches = {}
        i = 0
        task_size = len(predicates) * len(vocab_vectors)
        for p in predicates:
            p_transformed = transform_predicate(p)
            vec = model.get_word_vector(p_transformed)
            best_match = None
            min_distance = 1.0
            for p_v_idx, (goal_relation, p_pred, p_v) in enumerate(vocab_vectors):
                current_distance = abs(cosine(vec, p_v))
                f.write('{}\t{}\t{}\n'.format(p, p_pred, current_distance))
                if is_predicate_equal_to_vocab(p, p_pred):
                    # identity is best match
                    min_distance = 0.0
                    best_match = (goal_relation, min_distance)
                    break
                if not best_match or current_distance < min_distance:
                    min_distance = current_distance
                    best_match = (goal_relation, min_distance)

                print_progress_with_eta('computing distances...', i, task_size, start_time)
                i += 1

            if p in best_matches:
                raise ValueError('p should not be twice in predicates (duplicate found)')
            f.write('best:{}\t{}\t{}\n'.format(p, best_match[0], best_match[1]))
            best_matches[p] = (best_match[0], best_match[1])
        return best_matches


def canonicalize_predicates(best_matches: {str: (str, float)}, min_distance_threshold: float, document_collection: str):
    """
    Canonicalizes Predicates by resolving synonymous predicates. This procedure updates the database
    :param best_matches: dictionary which maps a predicate to a canonicalized predicate and a distance score
    :param min_distance_threshold: all predicates that have a match with a distance blow minimum threshold distance are canonicalized
    :param document_collection: the document collection to canonicalize
    :return: None
    """
    session = Session.get()
    start_time = datetime.now()

    logging.info('Finalizing update plan...')
    pred_can2preds = defaultdict(set)
    for pred, (pred_canonicalized, min_distance) in best_matches.items():
        if min_distance > min_distance_threshold:
            pred_canonicalized = PRED_TO_REMOVE
        pred_can2preds[pred_canonicalized].add(pred)

    logging.info(f'Execute {len(pred_can2preds)} update jobs...')
    task_size = len(pred_can2preds)
    i = 0
    for pred_canonicalized, preds in pred_can2preds.items():
        stmt = update(Predication).where(and_(Predication.predicate.in_(preds),
                                              Predication.document_collection == document_collection)). \
            values(predicate_canonicalized=pred_canonicalized)
        session.execute(stmt)
        print_progress_with_eta('updating...', i, task_size, start_time, print_every_k=1)
        i += 1

    logging.info('Committing updates...')
    session.commit()


def canonicalize_predication_table(word2vec_model, output_distances, predicate_vocabulary, document_collection=None,
                                   min_distance_threshold=0.4, min_predicate_threshold=0.001):
    """
    Canonicalizes the predicates in the database
    :param word2vec_model: a Word2Vec model
    :param output_distances: a file where the predicate mapping will be stored
    :param predicate_vocabulary: the predicate vocabulary
    :param document_collection: the document collection to canonicalize
    :param min_predicate_threshold: how often should a predicate occur at minimum (0.1 means that the predicate appears in at least 10% of all extractions)
    :param min_distance_threshold: all predicates that have a match with a distance blow minimum threshold distance are canonicalized
    :return: None
    """
    logging.info('Loading Word2Vec model...')
    model = fasttext.load_model(word2vec_model)
    if not predicate_vocabulary:
        logging.info('Creating predicate vocabulary...')
        pred_vocab = create_predicate_vocab()
    else:
        pred_vocab = predicate_vocabulary
    logging.info('{} predicates in vocabulary'.format(len(pred_vocab)))
    logging.info('Retrieving predicates from db...')
    predicates_with_count = Predication.query_predicates_with_count(session=Session.get(),
                                                                    document_collection=document_collection)
    logging.info(f'{len(predicates_with_count)} predicates with count retrieved')
    logging.info('Filtering with minimum count...')
    predicates = filter_predicate_list(predicates_with_count, min_predicate_threshold)
    logging.info('{} predicates obtained'.format(len(predicates)))
    logging.info('Matching predicates...')
    best_matches = match_predicates(model, predicates, pred_vocab, output_distances)
    logging.info('Canonicalizing predicates...')
    canonicalize_predicates(best_matches, min_distance_threshold, document_collection)
    logging.info('Finished')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("word2vec_model", help='word2vec file')
    parser.add_argument("output_distances", help='tsv export for distances')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    canonicalize_predication_table(args.word2vec_model, args.output_distances,
                                   predicate_vocabulary=create_predicate_vocab())


if __name__ == "__main__":
    main()
