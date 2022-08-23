import json
import logging

from narraint.config import BACKEND_CONFIG
from narraint.frontend.entity.autocompletion import AutocompletionUtil
from narraint.frontend.entity.entitytagger import EntityTagger
from narrant.build_all_indexes import build_entity_indexes
from narrant.build_all_tagging_indexes import build_tagging_indexes


def build_service_indexes():
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('========== You should go and pick up some Coffee ===========')
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('Computing tagging index...')

    entity_tagger = EntityTagger.instance(load_index=False)
    entity_tagger.store_index()

    ac = AutocompletionUtil.instance(load_index=False)
    ac.build_autocompletion_index()

    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('================= ! Finally ! You Did it ! =================')
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('Building narrative service indexes...')
    with open(BACKEND_CONFIG) as f:
        config = json.load(f)
    print('Some indexes rely on the tag / predication table of the database...')
    is_sqlite = False or ("use_SQLite" in config and config["use_SQLite"])
    if is_sqlite:
        database_name = config["SQLite_path"]
    else:
        database_name = config["POSTGRES_DB"]
    print(f'Your current database is: {database_name}')
    user_input = input('Continue with database setting? (y/yes)')
    user_input = user_input.lower()
    if 'y' in user_input or 'yes' in user_input:
        build_tagging_indexes()
        build_entity_indexes(complete=False, skip_mesh=False, force=True)
        build_service_indexes()
    else:
        print('user canceled index creation')


if __name__ == "__main__":
    main()
