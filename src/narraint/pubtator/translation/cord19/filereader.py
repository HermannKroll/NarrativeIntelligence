import json


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
            self.abstract = ' '.join(self.abstract)

    def __repr__(self):
        return f'{self.paper_id}: {self.abstract[:200]}... {self.body_text[:200]}...'

    def get_paragraph(self, art_par_id):
        """
        Get the text of the abstract or the full text paraphs
        :param art_par_id: 0 refers to abstract, >=1 to full text paragraphs
        :return:
        """
        return self.body_texts[art_par_id-1] if art_par_id > 0 else self.abstract
