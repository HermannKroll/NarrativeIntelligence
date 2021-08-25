import argparse
import logging
from datetime import datetime

import stanza
from spacy.lang.en import English

from narraint.cleaning.relation_vocabulary import RelationVocabulary
from narraint.extraction.extraction_utils import filter_document_sentences_without_tags
from narraint.extraction.pathie.core import PathIEDependency, PathIEToken, pathie_extract_facts_from_sentence
from narrant.progress import print_progress_with_eta
from narrant.pubtator.count import count_documents


def pathie_stanza_extract_interactions(doc2sentences, doc2tags, file_count, output,
                                       predicate_vocabulary: {str: [str]}):
    """
    Perform extraction based on PathIE Stanza
    Invokes Stanza to produce the corresponding tokenization and dependency parsing
    :param doc2sentences: a dict that maps a document id to a list of sentences
    :param doc2tags: a dict that maps a document to its corresponding tags
    :param file_count: the number of files for progress estimation
    :param output: the output that should be written
    :param predicate_vocabulary: the predicate vocabulary if special words are given
    :return: None
    """
    start_time = datetime.now()
    logging.info('Initializing Stanza Pipeline...')
    nlp = stanza.Pipeline(lang='en', processors='tokenize,mwt,pos,lemma,depparse', use_gpu=True)

    first_line = True
    with open(output, 'wt') as f_out:
        for idx, (doc_id, sentences) in enumerate(doc2sentences.items()):
            doc_tags = doc2tags[doc_id]
            doc_content = ''.join(sentences)
            # perform the stanza call
            processed_doc = nlp(doc_content)
            extracted_tuples = []
            for sent in processed_doc.sentences:
                # convert stanza tokens and dependencies to PathIE tuples
                sent_dependencies = []
                for dep in sent.dependencies:
                    w1, relation, w2 = dep
                    sent_dependencies.append(PathIEDependency(w1.id, w2.id, relation))
                sent_tokens = []
                for t in sent.tokens:
                    # fake before and after tokens because they are not available in stanza
                    sent_tokens.append(PathIEToken(t.text, t.text.lower(), "", " ",
                                                   t.id[0], t.start_char, t.end_char,
                                                   t.words[0].pos, t.words[0].lemma))

                extracted_tuples.extend(pathie_extract_facts_from_sentence(doc_id, doc_tags, sent_tokens,
                                                                           sent_dependencies,
                                                                           predicate_vocabulary=predicate_vocabulary))

            print_progress_with_eta("pathie: processing documents...", idx, file_count, start_time, print_every_k=1)
            for e_tuple in extracted_tuples:
                line = '\t'.join([str(t) for t in e_tuple])
                if first_line:
                    first_line = False
                    f_out.write(line)
                else:
                    f_out.write('\n' + line)


def run_stanza_pathie(input_file, output, predicate_vocabulary: {str: [str]} = None):
    """
    Executes PathIE via Stanza
    :param input_file: the PubTator input file (tags must be included)
    :param output: extractions will be written to output
    :param predicate_vocabulary: the predicate vocabulary if special words are given
    :return: None
    """
    logging.info('Init spacy nlp...')
    spacy_nlp = English()  # just the language with no model
    sentencizer = spacy_nlp.create_pipe("sentencizer")
    spacy_nlp.add_pipe(sentencizer)

    # Prepare files
    doc_count = count_documents(input_file)
    logging.info('{} documents counted'.format(doc_count))

    doc2sentences, doc2tags = filter_document_sentences_without_tags(doc_count, input_file, spacy_nlp)
    amount_files = len(doc2tags)

    if amount_files == 0:
        print('no files to process - stopping')
    else:
        start = datetime.now()
        # Process output
        pathie_stanza_extract_interactions(doc2sentences, doc2tags, amount_files, output,
                                           predicate_vocabulary=predicate_vocabulary)
        print(" done in {}".format(datetime.now() - start))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="PubTator file / directory of PubTator files - PubTator files must include Tags")
    parser.add_argument("output", help="PathIE output file")
    parser.add_argument('--relation_vocab', default=None, help='Path to a relation vocabulary (json file)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    if args.relation_vocab:
        relation_vocab = RelationVocabulary()
        relation_vocab.load_from_json(args.relation_vocab)

        run_stanza_pathie(args.input, args.output, predicate_vocabulary=relation_vocab.relation_dict)
    else:
        run_stanza_pathie(args.input, args.output)


if __name__ == "__main__":
    main()
