import os
from collections import defaultdict

from narraint import tools
from narraint.backend.models import Tag, Document
from narraint.entity.enttypes import ENTITY_TYPES
from narraint.pubtator.regex import TAG_LINE_NORMAL, CONTENT_ID_TIT_ABS


class TaggedEntity:

    def __init__(self, tag_tuple=None, document=None, start=None, end=None, text=None, ent_type=None, ent_id = None):
        self.document = int(tag_tuple[0]) if tag_tuple else document
        self.start = int(tag_tuple[1]) if tag_tuple else start
        self.end = int(tag_tuple[2]) if tag_tuple else end
        self.text = tag_tuple[3] if tag_tuple else text
        self.ent_type = ENTITY_TYPES[tag_tuple[4] if tag_tuple else ent_type]
        self.ent_id = tag_tuple[5] if tag_tuple else ent_id
        if self.ent_type not in ENTITY_TYPES:
            raise KeyError('entity type not supported yet: {}'.format(tag_tuple))

    def __str__(self):
        return Tag.create_pubtator(self.document, self.start, self.end, self.text, self.ent_type, self.ent_id)

    def __repr__(self):
        return "<Entity {},{},{},{},{}>".format(self.start, self.end, self.text, self.ent_type, self.ent_id)

    def __eq__(self, other):
        return self.document == other.document and self.start == other.start and self.end == other.end \
            and self.text == other.text and self.ent_type == other.ent_type and self.ent_id == other.ent_id


class Sentence:
    def __init__(self, sid, text, start, end) -> None:
        super().__init__()
        self.start = start
        self.text = text
        self.sid = sid
        self.end = end

    def __str__(self):
        return f'<Sentence {self.sid}, {self.start}, {self.end}, {self.text}'

    def __repr__(self):
        return str(self)


def parse_tag_list(path_or_str):
    content = tools.read_if_path(path_or_str)
    reg_result = TAG_LINE_NORMAL.findall(content)
    return [TaggedEntity(t) for t in reg_result] if reg_result else []

class TaggedDocument:

    def __init__(self, pubtator_content, spacy_nlp=None):
        """
        initialize a pubtator document
        :param pubtator_content: content of a pubtator file or a pubtator filename
        """
        pubtator_content = tools.read_if_path(pubtator_content)
        self.id, self.title, self.abstract = CONTENT_ID_TIT_ABS.match(pubtator_content).group(1, 2, 3)
        self.title = self.title.strip()
        self.abstract = self.abstract.strip()
        self.id = int(self.id)
        self.tags = [TaggedEntity(t) for t in TAG_LINE_NORMAL.findall(pubtator_content)]
        self.entity_names = {t.text.lower() for t in self.tags}
        if spacy_nlp:
            # Indexes
            # self.mesh_by_entity_name = {}  # Use to select mesh descriptor by given entity
            self.sentence_by_id = {}  # Use to build mesh->sentence index
            self.entities_by_ent_id = defaultdict(list)  # Use Mesh->TaggedEntity index to build Mesh->Sentence index
            self.sentences_by_ent_id = defaultdict(set)  # Mesh->Sentence index
            self.entities_by_sentence = defaultdict(set)  # Use for _query processing
            self._create_index(spacy_nlp)

    def clean_tags(self):
        clean_tags = self.tags.copy()
        for tag1 in self.tags:
            if not tag1.document or not tag1.start or not tag1.end or not tag1.text or not tag1.ent_type or not tag1.ent_id:
                clean_tags.remove(tag1)
            else:
                for tag2 in self.tags:
                    if tag2.start <= tag1.start and tag2.end >= tag1.end and tag1.text.lower() != tag2.text.lower():
                        clean_tags.remove(tag1)
                        break
        self.tags = sorted(clean_tags, key=lambda t: (t.start, t.end, t.ent_id))

    def _create_index(self, spacy_nlp):
        # self.mesh_by_entity_name = {t.text.lower(): t.mesh for t in self.tags if
        #                            t.text.lower() not in self.mesh_by_entity_name}
        if self.title[-1] == '.':
            content = f'{self.title} {self.abstract}'
            offset = 1
        else:
            content = f'{self.title}. {self.abstract}'
            offset = 2
        doc_nlp = spacy_nlp(content)
        for idx, sent in enumerate(doc_nlp.sents):
            sent_str = str(sent)
            start_pos = content.index(sent_str)
            end_pos = content.index(sent_str) + len(sent_str)
            if start_pos > len(self.title):
                start_pos -= offset
                end_pos -= offset

            self.sentence_by_id[idx] = Sentence(
                idx,
                sent_str,
                start_pos,
                end_pos
            )

        for tag in self.tags:
            self.entities_by_ent_id[tag.ent_id].append(tag)

        for ent_id, entities in self.entities_by_ent_id.items():
            for entity in entities:
                for sid, sent in self.sentence_by_id.items():
                    if sent.start <= entity.start <= sent.end:
                        self.sentences_by_ent_id[ent_id].add(sid)
                        self.entities_by_sentence[sid].add(entity)

    def __str__(self):
        return Document.create_pubtator(self.id, self.title, self.abstract)+"".join([str(t) for t in self.tags])+"\n"

    def __repr__(self):
        return "<Document {} {}>".format(self.id, self.title)


class TaggedDocumentCollection:

    def __init__(self, filename):
        self.docs = []
        self.docs_by_id = {}

        # read from a single pubtator file
        with open(filename, 'r') as f:
            doc_lines = []
            for line in f:
                # split at only '\n' (empty new line)
                if line == '\n':
                    # skip multiple new lines
                    if len(doc_lines) == 0:
                        continue
                    self._add_doc_from_content(''.join(doc_lines))
                    doc_lines = []
                else:
                    doc_lines.append(line)

    def _add_doc_from_content(self, content):
        doc = TaggedDocument(content)
        self.docs.append(doc)
        if doc.id in self.docs_by_id:
            raise Exception('ID already included in collection')
        self.docs_by_id[doc.id] = doc
