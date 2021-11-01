import logging
import os
from datetime import datetime

from spacy.lang.en import English

from narraint.config import DATA_DIR
from kgextractiontoolbox.extraction.extraction_utils import filter_document_sentences_without_tags
from kgextractiontoolbox.extraction.openie.main import run_corenlp_openie
from kgextractiontoolbox.extraction.openie6.main import openie6_run
from kgextractiontoolbox.extraction.pathie.main import run_pathie
from kgextractiontoolbox.extraction.pathie_stanza.main import run_stanza_pathie
from narrant.pubtator.count import count_documents

PERFORMANCE_TEST_DIR = os.path.join(DATA_DIR, 'performance/')

OUT_PATHIE = os.path.join(PERFORMANCE_TEST_DIR, 'pathie_output.tsv')
OUT_PATHIE_STANZA = os.path.join(PERFORMANCE_TEST_DIR, 'pathie_stanza_output.tsv')
OUT_OPENIE = os.path.join(PERFORMANCE_TEST_DIR, 'openie_output.tsv')
OUT_OPENIE6 = os.path.join(PERFORMANCE_TEST_DIR, 'openie6_output.tsv')
# TEST_FILE = os.path.join(PERFORMANCE_TEST_DIR, 'small_test.pubtator')
TEST_FILE = os.path.join(PERFORMANCE_TEST_DIR, 'performance_evaluation_sample_10k.tagged.pubtator')
TIME_FILE = os.path.join(PERFORMANCE_TEST_DIR, "runtimes.tsv")
TEST_COLLECTION = 'PubMed'

RUNS = 3
RUN_DOC_ANALYSES = True
RUN_PATHIE = True
RUN_STANZA_PATHIE = True
RUN_CORENLP_OPENIE = True
RUN_OPENIE6 = True


def main():
    logging.basicConfig(level="ERROR")

    if RUN_DOC_ANALYSES:
        logging.info('Init spacy nlp...')
        spacy_nlp = English()  # just the language with no model
        sentencizer = spacy_nlp.create_pipe("sentencizer")
        spacy_nlp.add_pipe(sentencizer)
        # Prepare files
        doc_count = count_documents(TEST_FILE)
        logging.info('{} documents counted'.format(doc_count))
        doc2sentences, doc2tags = filter_document_sentences_without_tags(doc_count, TEST_FILE, spacy_nlp)

        tag_count = sum([len(tags) for doc_id, tags in doc2tags.items()])
        sentence_count = sum([len(sents) for doc_id, sents in doc2sentences.items()])
        logging.error(f'Found {tag_count} tags and {sentence_count}')

    times = []
    for i in range(0, RUNS):
        logging.error('=' * 60)
        logging.error(f'      Run {i + 1}           ')
        logging.error('=' * 60)

        start = datetime.now()
        if RUN_PATHIE:
            logging.error('Running PathIE...')
            run_pathie(TEST_FILE, OUT_PATHIE, workers=32)

        pathie_time = datetime.now() - start
        logging.error(f'PathIE takes {pathie_time}s')

        start = datetime.now()
        if RUN_STANZA_PATHIE:
            logging.info('Running Stanza PathIE...')
            run_stanza_pathie(TEST_FILE, OUT_PATHIE_STANZA)

        pathie_stanza_time = datetime.now() - start
        logging.error(f'PathIEStanza takes {pathie_stanza_time}s')

        start = datetime.now()
        if RUN_CORENLP_OPENIE:
            logging.error('Running StanfordCoreNLP OpenIE...')
            run_corenlp_openie(TEST_FILE, OUT_OPENIE)

        openie_time = datetime.now() - start
        logging.error(f'CoreNLP OpenIE takes {openie_time}s')

        start = datetime.now()
        if RUN_OPENIE6:
            logging.info('Running OpenIE6...')
            openie6_run(TEST_FILE, OUT_OPENIE6)

        openie6_time = datetime.now() - start
        logging.error(f'CoreNLP OpenIE6 takes {openie6_time}s')

        times.append((pathie_time, pathie_stanza_time, openie_time, openie6_time))

    with open(TIME_FILE, 'wt') as f:
        f.write('PathIE\tPathIEStanza\tOpenIE\tOpenIE6')
        for t_pi, t_pi_s, t_oi, t_oi6 in times:
            f.write(f'\n{t_pi}\t{t_pi_s}\t{t_oi}\t{t_oi6}')

    print(times)


if __name__ == '__main__':
    main()
