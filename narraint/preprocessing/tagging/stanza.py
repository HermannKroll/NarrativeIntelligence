import os
from datetime import datetime

import stanza

from narraint.preprocessing.tagging.base import BaseTagger
from narraint.pubtator.document import TaggedDocument, TaggedEntity


class StanzaTagger(BaseTagger):
    __name__ = "StanzaNER"
    __version__ = "1.0"

    def __init__(self, *args, **kwargs):
        self.__stanza = None
        super().__init__(*args, **kwargs)

    def tag_doc(self, in_doc: TaggedDocument) -> TaggedDocument:
        pmid, title, abstact = in_doc.id, in_doc.title, in_doc.abstract
        content = title.strip() + " " + abstact.strip()
        content = content.lower()

        stanza_doc = self.__stanza(content)
        for entity in stanza_doc.entities:
            start, end = entity.start_char, entity.end_char
            ent_str = entity.text
            ent_id = entity.text
            ent_type = entity.type
            in_doc.tags.append(TaggedEntity(document=in_doc.id, start=start, end=end, text=ent_str,
                                            ent_type=ent_type, ent_id=ent_id))
        return in_doc

    def prepare(self, resume=False, use_gpu=True):
        self.__stanza = stanza.Pipeline(lang='en', processors='tokenize,mwt,ner', use_gpu=use_gpu)
        pass

    def run(self):
        pass

    def get_progress(self):
        pass

    def get_tags(self):
        pass

    def get_successful_ids(self):
        pass
