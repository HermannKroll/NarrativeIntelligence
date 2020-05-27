import glob
import json
import csv
from argparse import ArgumentParser
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from narraint.backend import models
from narraint.backend.database import Session
from narraint.backend.models import Document
from narraint.progress import print_progress_with_eta

UNIQUE_ID_START = 100000
NEXT_DOCUMENT_ID_OFFSET = 100000


class FileReader:
    def __init__(self, file_path):
        with open(file_path) as file:
            content = json.load(file)
            self.paper_id = content['paper_id']
            self.title = ""
            self.abstract = []
            self.body_texts = []
            # Title
            self.title = content['metadata']["title"]
            # Abstract
            if 'abstract' in content:
                for entry in content['abstract']:
                    self.abstract.append(entry['text'])
            # Body text
            for entry in content['body_text']:
                self.body_texts.append(entry['text'])
            self.abstract = '\n'.join(self.abstract)

    def __repr__(self):
        return f'{self.paper_id}: {self.abstract[:200]}... {self.body_text[:200]}...'


def main():
    parser = ArgumentParser(description="Collect and convert PMC files from a list of pmc-ids")
    parser.add_argument("input", help="Root Directory of Cord19m2 data set")
    parser.add_argument("metadata", help="Path to metadata.csv file")
    parser.add_argument("output", help="Output of the resulting Pubtator file")
    args = parser.parse_args()

    translator = Translator(args.input, args.output, args.metadata)
    dict_list = read_metadata(args.metadata)


class Translator:
    def __init__(self, input_dir, output_dir, metadata_file):
        self.metadata_dict = read_metadata(metadata_file)
        self.session = Session.get()

    """
    recursively searches for all .json files in input_dir, sanitizes them and converts them to a pubtator format. 
    :parm input_dir: directory containing the json files
    :param output_dir: an (existing) file path to write the pubtator output to
    """
    def translate(input_dir, output_file):
        print('searching all json files in {}'.format(input_dir))
        all_json = glob.glob(f'{input_dir}/**/*.json', recursive=True)
        print('{} json files found'.format(len(all_json)))
        start_time = datetime.now()
        with open(output_file, 'w') as f, open(output_file + '.info.csv', 'w') as f_info:
            f_info.write('document_id\tpaper_id')
            for idx, json_file in enumerate(all_json):
                try:
                    file = FileReader(json_file)
                    doc_id = UNIQUE_ID_START + (NEXT_DOCUMENT_ID_OFFSET * idx)
                    # export title + abstract
                    if len(file.abstract) > 0:
                        content = Document.create_pubtator(doc_id, file.title, file.abstract)
                        f.write(content + '\n')

                    for body_text_id, body_text in enumerate(file.body_texts):
                        if body_text_id >= NEXT_DOCUMENT_ID_OFFSET:
                            raise ValueError('Overflow body id - increase id range for document bodies')
                        artificial_doc_id = doc_id + body_text_id + 1
                        content = Document.create_pubtator(artificial_doc_id, "Section", body_text)
                        f.write(content + '\n')

                    f_info.write('\n{}\t{}'.format(doc_id, file.paper_id))
                    print_progress_with_eta('converting', idx, len(all_json), start_time)
                except KeyError:
                    print('skip: {}'.format(json_file))


    def insert_translation(art_id, sha):

        insert_query = insert(models.Cord19Translation).values(

        )


def read_metadata(metadata_file):
    with open(metadata_file, 'r') as f:
        reader = csv.DictReader(f)
        dict_list = []
        for d in reader:
            for k in d.keys():
                d[k] = d[k].split(";") # Iterpret ; splitted values as list
            dict_list.append(d)
        return dict_list

if __name__ == "__main__":
    main()
