import json
import logging
from typing import Union
from pathlib import Path

from kgextractiontoolbox.document.document import TaggedDocument
from narraint.pollux.doctranslation import SourcedDocument, DocumentTranslationLoader, main


class PolluxLoader(DocumentTranslationLoader):
    def __init__(self, collection):
        super().__init__(collection)

    # make this an overridable class and include it into toolbox
    def read_sourced_documents(self, file: Union[Path, str]):
        if not type(file) == Path:
            file = Path(file)
        with open(file) as f:
            for line in f:
                content = json.loads(line)
                if not content["languages"] or 'eng' not in content["languages"]:
                    continue
                source_id = content["id"]
                source = file.name
                title = content["title"].encode('unicode_escape').decode('unicode_escape')
                for n, abstract in enumerate(content["abstracts"]):
                    doc = TaggedDocument(title=title, abstract=abstract['value'].encode('unicode_escape').decode(
                        'unicode_escape'))
                    yield SourcedDocument(f"{source_id}:{n}", source, doc)

    def count_documents(self, file: Union[Path, str]):
        count = 0
        for line in open(file): count += 1
        return count



if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    main(PolluxLoader)
