import logging
from collections import defaultdict

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.backend.models import Document, Tag
from kgextractiontoolbox.document.export import export
from kgextractiontoolbox.extraction.loading.load_openie_extractions import load_openie_tuples, OpenIEEntityFilterMode
from kgextractiontoolbox.extraction.openie6.main import openie6_run

BENCHMARK_FILE = "/home/kroll/NarrativeIntelligence/data/trex/trex_statements_spo.tsv"
TREX_COLLECTION = "Trex_Benchmark"
TREX_DOCUMENTS = "/home/kroll/NarrativeIntelligence/data/trex/trex_documents.json"
TREX_OPENIE6_OUTPUT = "/home/kroll/NarrativeIntelligence/data/trex/openie6.tsv"

LOAD_TREX_BENCHMARK_DATA_INTO_DB = False
EXPORT_TREX_DOCUMENTS = True

RUN_OPENIE6 = True
LOAD_OPENIE6 = True

TREX_ENTITY_TYPE = "NA"


def read_trex_benchmark():
    benchmark_entries = []
    entry_by_relation = defaultdict(list)
    with open(BENCHMARK_FILE, 'rt') as f:
        for line in f:
            data = line.split('\t')

            doc_id, subject_str, subject_id, predicate, relation, object_str, object_id, sentence_txt = data

            entry = (subject_str, subject_id, predicate, relation, object_str, object_id, sentence_txt)
            benchmark_entries.append(entry)
            entry_by_relation[(predicate, relation)].append(entry)

    return benchmark_entries, entry_by_relation


def load_trex_benchmark_into_db(benchmark_entries):
    document_values = []
    tag_values = []
    session = Session.get()
    for idx, entry in enumerate(benchmark_entries):
        subject_str, subject_id, predicate, relation, object_str, object_id, sentence_txt = entry
        document_values.append(dict(id=idx,
                                    collection=TREX_COLLECTION,
                                    title=sentence_txt,
                                    abstract=""))

        tag_values.append(dict(ent_type=TREX_ENTITY_TYPE,
                               ent_id=subject_id,
                               ent_str=subject_str,
                               start=0,
                               end=0,
                               document_id=idx,
                               document_collection=TREX_COLLECTION))

        tag_values.append(dict(ent_type=TREX_ENTITY_TYPE,
                               ent_id=object_id,
                               ent_str=object_str,
                               start=0,
                               end=0,
                               document_id=idx,
                               document_collection=TREX_COLLECTION))

    # Inserting values
    logging.info(f'Inserting: {len(document_values)} documents and {len(tag_values)} '
                 f'tags into db (collection: {TREX_COLLECTION})')

    Document.bulk_insert_values_into_table(session, document_values)
    Tag.bulk_insert_values_into_table(session, tag_values)
    logging.info('Finished')


def main():
    # parser = argparse.ArgumentParser("Export documents from database with tags and predications")
    # parser.add_argument("-c", "--collection", help="Document collection")
    # parser.add_argument("-i", "--ids", help="Document ids", nargs="*")
    # parser.add_argument("output", help="output file")
    # args = parser.parse_args(args)
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    benchmark_entries, entries_by_relation = read_trex_benchmark()

    if LOAD_TREX_BENCHMARK_DATA_INTO_DB:
        load_trex_benchmark_into_db(benchmark_entries)

    if EXPORT_TREX_DOCUMENTS:
        export(TREX_DOCUMENTS, TREX_ENTITY_TYPE, collection=TREX_COLLECTION, content=True, export_format="json")

    if RUN_OPENIE6:
        logging.info('Running OpenIE6...')
        openie6_run(TREX_DOCUMENTS, TREX_OPENIE6_OUTPUT, no_entity_filter=True)

    if LOAD_OPENIE6:
        logging.info('Loading OpenIE 6.0 extractions...')
        load_openie_tuples(TREX_OPENIE6_OUTPUT, TREX_COLLECTION,
                           entity_filter=OpenIEEntityFilterMode.PARTIAL_ENTITY_FILTER,
                           extraction_type="OpenIE6_PF")

        load_openie_tuples(TREX_OPENIE6_OUTPUT, TREX_COLLECTION,
                           entity_filter=OpenIEEntityFilterMode.ONLY_SUBJECT_EXACT,
                           extraction_type="OpenIE6_SF")
        logging.info('finished')


if __name__ == '__main__':
    main()
