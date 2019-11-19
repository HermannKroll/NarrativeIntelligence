import re


class PubTatorDoc:

    def __init__(self):
        self.PUBTATOR_REGEX = re.compile(r"(\d+)\|t\|(.*?)\n\d+\|a\|(.*?)\n")

        self.annotations = []
        self.pmid = None
        self.title = None
        self.abstract = None

    def load_from_file(self, filename):
        with open(filename) as f:
            document = f.read().strip()
        match = self.PUBTATOR_REGEX.match(document)
        if not match:
            print(f"Error: Ignoring {filename} (no pubtator format found)")
            return
        else:
            self.pmid, self.title, self.abstract = match.group(1, 2, 3)

        # lookup whether annotations are included
        if document.count('\n') > 3:
            for line in document.split('\n')[2:]:
                # skip empty lines
                if len(line) == 0:
                    continue

                components = line.split('\t')
                start = components[1]
                stop = components[2]
                term = components[3]
                entity_type = components[4]
                if len(components) == 6:
                    entity_id = components[5]
                else:
                    entity_id = ''
                t = (start, stop, term, entity_type, entity_id)
                self.annotations.append(t)
