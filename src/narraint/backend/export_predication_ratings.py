import json
import logging
from argparse import ArgumentParser

from narraint.backend.database import SessionExtended
from narraint.backend.models import PredicationRating


def export_predication_ratings(output_file: str):
    """
    Exports the Predication Ratings as a JSON file
    :param output_file: the output file path
    :return: None
    """
    logging.info(f'Exporting predication ratings to {output_file}...')

    session = SessionExtended.get()
    ratings = []
    logging.info('Querying information...')
    for res_dict in PredicationRating.query_predication_ratings_as_dicts(session):
        ratings.append(res_dict)

    logging.info(f'Writing JSON file with {len(ratings)} elements...')
    with open(output_file, 'wt') as f:
        json.dump(ratings, f, sort_keys=True, indent=4)
    logging.info('Finished')


def main():
    parser = ArgumentParser()
    parser.add_argument("output", help="Predication ratings will be stored to this file in JSON")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    export_predication_ratings(args.output)


if __name__ == "__main__":
    main()
