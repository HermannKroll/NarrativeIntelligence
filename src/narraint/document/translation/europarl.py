import json
import logging
from pathlib import Path
from typing import Union

from kgextractiontoolbox.document.document import TaggedDocument
from narraint.pollux.doctranslation import SourcedDocument, DocumentTranslationLoader, main


class EuroparlLoader(DocumentTranslationLoader):
    def __init__(self, collection, loader_kwargs=None):
        super().__init__(collection)

    # make this an overridable class and include it into toolbox
    def read_sourced_documents(self, file: Union[Path, str]):
        if not type(file) == Path:
            file = Path(file)
        with open(file) as f:
            doc_content = f.read()

        content = json.loads(doc_content)
        for speech in content:
            if not speech["speaker_id"] or not speech['chapter_id']:
                continue
            source_id = speech["speaker_id"] + '_' + speech['chapter_id']
            source = file.name
            title = ""
            if 'chapter_title' in speech and speech['chapter_title']:
                title = speech['chapter_title']
            if title:
                title = title + ': '
            if 'speaker_name' in speech and speech['speaker_name']:
                title = title + speech["speaker_name"]
            abstract = speech['text']
            if not title or not abstract:
                continue
            # for n, abstract in enumerate(content["abstracts"]):
            doc = TaggedDocument(title=title.strip(), abstract=abstract.strip())
            yield SourcedDocument(f"{source_id}", source, doc)

    def count_documents(self, file: Union[Path, str]):
        with open(file) as f:
            doc_content = f.read()
        content = json.loads(doc_content)
        return len(content)


if __name__ == '__main__':
    logging.basicConfig(level="INFO")
    main(EuroparlLoader)
