import json
import logging
from argparse import ArgumentParser

from narraint.backend.database import SessionExtended
from narraint.backend.models import SubstitutionGroupRating


def export_subgroup_ratings(output_file: str):
    """
    Exports the Substitution Group Ratings as a JSON file
    :param output_file: the output file path
    :return: None
    """
    logging.info(f'Exporting substitution group ratings to {output_file}...')

    session = SessionExtended.get()
    ratings = []
    logging.info('Querying information...')
    for res_dict in SubstitutionGroupRating.query_subgroup_ratings_as_dicts(session):
        ratings.append(res_dict)

    logging.info(f'Writing JSON file with {len(ratings)} elements...')
    with open(output_file, 'wt') as f:
        json.dump(ratings, f, indent=4)
    logging.info('Finished')


def main():
    parser = ArgumentParser()
    parser.add_argument("output", help="Substitution Group ratings will be stored to this file in JSON")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    export_subgroup_ratings(args.output)


if __name__ == "__main__":
    main()
