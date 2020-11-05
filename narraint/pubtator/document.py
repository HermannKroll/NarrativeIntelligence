from narraint.entity.enttypes import ENTITY_TYPES
from narraint.pubtator.regex import TAG_LINE_NORMAL, CONTENT_ID_TIT_ABS


class TaggedEntity:
    def __init__(self, tag_tuple):
        self.document = int(tag_tuple[0])
        self.start = int(tag_tuple[1])
        self.end = int(tag_tuple[2])
        self.text = tag_tuple[3]

        if tag_tuple[4] not in ENTITY_TYPES:
            raise KeyError('entity type not supported yet: {}'.format(tag_tuple))

        self.type = ENTITY_TYPES[tag_tuple[4]]
        self.ent_id = tag_tuple[5]

    def __str__(self):
        return "<Entity {},{},{},{},{}>".format(self.start, self.end, self.text, self.type, self.ent_id)


class Sentence:
    def __init__(self, sid, text, start, end) -> None:
        super().__init__()
        self.start = start
        self.text = text
        self.sid = sid
        self.end = end


class TaggedDocument:

    def __init__(self, pubtator_content, spacy_nlp=None):
        """
        initialize a pubtator document
        :param pubtator_content: content of a pubtator file or a pubtator filename
        """
        self.id, self.title, self.abstract = CONTENT_ID_TIT_ABS.match(pubtator_content).group(1, 2, 3)
        self.id = int(self.id)
        self.tags = [TaggedEntity(t) for t in TAG_LINE_NORMAL.findall(pubtator_content)]
        self.entity_names = {t.text.lower() for t in self.tags}
        if spacy_nlp:
            # Indexes
            # self.mesh_by_entity_name = {}  # Use to select mesh descriptor by given entity
            self.sentence_by_id = {}  # Use to build mesh->sentence index
            self.entities_by_ent_id = {}  # Use Mesh->TaggedEntity index to build Mesh->Sentence index
            self.sentences_by_ent_id = {}  # Mesh->Sentence index
            self.entities_by_sentence = {}  # Use for _query processing
            self._create_index(spacy_nlp)

    def _create_index(self, spacy_nlp):
        # self.mesh_by_entity_name = {t.text.lower(): t.mesh for t in self.tags if
        #                            t.text.lower() not in self.mesh_by_entity_name}
        content = f'{self.title}. {self.abstract}'
        doc_nlp = spacy_nlp(content)
        for idx, sent in enumerate(doc_nlp.sents):
            self.sentence_by_id[idx] = Sentence(
                idx,
                sent.lower(),
                content.index(sent),
                content.index(sent) + len(sent),
            )

        for tag in self.tags:
            if tag.ent_id not in self.entities_by_ent_id:
                self.entities_by_ent_id[tag.ent_id] = []
            self.entities_by_ent_id[tag.ent_id] += [tag]

        for ent_id, entities in self.entities_by_ent_id.items():
            if ent_id not in self.sentences_by_ent_id:
                self.sentences_by_ent_id[ent_id] = set()
            for entity in entities:
                for sid, sent in self.sentence_by_id.items():
                    if sent.start <= entity.start <= sent.end:
                        self.sentences_by_ent_id[ent_id].add(sid)
                        if sid not in self.entities_by_sentence:
                            self.entities_by_sentence[sid] = set()
                        self.entities_by_sentence[sid].add(entity)

    def __str__(self):
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

