import os
import shutil
import logging
from argparse import ArgumentParser

import tempfile

from narraint.preprocessing.tagging.metadictagger import MetaDicTagger
from narraint.pubtator import count
from narraint.config import PREPROCESS_CONFIG
from narraint.entity.enttypes import TAG_TYPE_MAPPING, DALL
from narraint.preprocessing.config import Config
from narraint.pubtator.sanitize import filter_and_sanitize
from narraint.preprocessing.preprocess import init_preprocess_logger, init_sqlalchemy_logger, \
    get_untagged_doc_ids_by_ent_type


def prepare_input(in_file:str, out_file: str, logger: logging.Logger, ent_types: set[str], collection: str) -> bool:
    if not os.path.exists(in_file):
        logger.error("Input file not found!")
        return False
    logger.info("Counting document ids...")
    in_ids = count.get_document_ids(in_file)
    todo_ids = set()
    for ent_type in ent_types:
        todo_ids |= get_untagged_doc_ids_by_ent_type(collection, in_ids, ent_type, MetaDicTagger, logger)
    filter_and_sanitize(in_file, out_file, todo_ids, logger)




def main(arguments=None):
    parser = ArgumentParser(description="Tag given documents in pubtator format and insert tags into database")

    group_tag = parser.add_argument_group("Tagging")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+", required=True)
    parser.add_argument("-c", "--collection", required=True)

    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=PREPROCESS_CONFIG,
                                help="Configuration file (default: {})".format(PREPROCESS_CONFIG))
    group_settings.add_argument("--loglevel", default="INFO")
    group_settings.add_argument("--workdir", default=None)

    group_settings.add_argument("-w", "--workers", default=1, help="Number of processes for parallelized preprocessing",
                                type=int)
    parser.add_argument("-y", "--yes_force", help="skip prompt for workdir deletion", action="store_true")

    parser.add_argument("input", help="composite pubtator file", metavar="IN_DIR")
    args = parser.parse_args(arguments)

    conf = Config(args.config)

    # create directories
    root_dir = root_dir = os.path.abspath(args.workdir) if args.workdir else tempfile.mkdtemp()
    log_dir = log_dir = os.path.abspath(os.path.join(root_dir, "log"))
    ext_in_file = args.input
    in_file = os.path.abspath(os.path.join(root_dir, "in.pubtator"))

    if os.path.exists(root_dir):
        if not args.yes_force:
            print(f"{root_dir} already exists, continue and delete?")
            resp = input("y/n")
            if resp not in {"y", "Y", "j", "J", "yes", "Yes"}:
                print("aborted")
                exit(0)
        else:
            shutil.rmtree(root_dir)

    os.makedirs(root_dir)
    os.makedirs(log_dir)

    # create loggers
    logger = init_preprocess_logger(os.path.join(log_dir, "preprocessing.log"), args.loglevel.upper())
    init_sqlalchemy_logger(os.path.join(log_dir, "sqlalchemy.log"), args.loglevel.upper())
    logger.info(f"Project directory:{root_dir}")

    ent_types = DALL if "DA" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]
    prepare_input(ext_in_file, in_file, logger, ent_types, args.collection)




if __name__ == '__main__':
    main()