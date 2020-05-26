import glob
import json
from argparse import ArgumentParser
from datetime import datetime

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
    parser.add_argument("input", help="Root Directory of Cord19m2 data setw")
    parser.add_argument("output", help="Output of the resulting Pubtator file")
    args = parser.parse_args()

    print('searching all json files in {}'.format(args.input))
    all_json = glob.glob(f'{args.input}/**/*.json', recursive=True)
    print('{} json files found'.format(len(all_json)))

    start_time = datetime.now()
    with open(args.output, 'w') as f, open(args.output+'.info.csv', 'w') as f_info:
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


if __name__ == "__main__":
    main()
