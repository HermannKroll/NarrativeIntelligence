import argparse
import glob
import json
import logging
from datetime import datetime

from narrant.progress import print_progress_with_eta


def _convert_wikidata_uri_to_id(uri):
    return uri.split('/')[-1]


def load_trex_dataset(input_dir, output_file):
    all_json = glob.glob(f'{input_dir}/**/*.json', recursive=True)

    start_time = datetime.now()
    files_len = len(all_json)
    logging.info('{} json files found'.format(files_len))

    with open(output_file, 'wt') as f_out:
        f_out.write('document_id\tsubject_str\tsubject_id\tpredicate\trelation\tobject_str\tobject_id\tsentence_text')
        for idx, json_file in enumerate(all_json):
            print_progress_with_eta('extracting from trex file', idx, files_len, start_time, print_every_k=1)
            with open(json_file) as file:
                docs_content = json.load(file)
                logging.info('Read {}'.format(json_file))
                for d_content in docs_content:
                    document_id = int(_convert_wikidata_uri_to_id(d_content['docid'])[1:])
                    text = d_content['text']
                    sentidx2id = {}
                    for s_idx, sentence_boundaries in enumerate(d_content['sentences_boundaries']):
                        sentidx2id[s_idx] = text[sentence_boundaries[0]:sentence_boundaries[1]]

                    for fact in d_content['triples']:

                        subject_ent = fact['subject']
                        subject_id = _convert_wikidata_uri_to_id(subject_ent['uri'])
                        subject_str = subject_ent['surfaceform']
                        predicate = fact['predicate']['surfaceform']
                        if not predicate:
                            continue # skip predicates that are not mapped to the text
                        relation = _convert_wikidata_uri_to_id(fact['predicate']['uri'])
                        object_ent = fact['object']
                        object_id = _convert_wikidata_uri_to_id(object_ent['uri'])
                        object_str = object_ent['surfaceform']
                        confidence = fact['confidence']
                        extraction_type = fact['annotator']
                        if extraction_type != 'SPOAligner':
                            continue # skip facts

                        sentence_txt = sentidx2id[int(fact['sentence_id'])]

                        result_str = f'\n{document_id}\t{subject_str}\t{subject_id}\t{predicate}\t{relation}\t{object_str}\t{object_id}\t{sentence_txt}'
                        f_out.write(result_str)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_file")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Loading TREX directory...')
    load_trex_dataset(args.input_dir, args.output_file)
    logging.info('Finished')


if __name__ == "__main__":
    main()
