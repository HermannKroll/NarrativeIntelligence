import re

CHEMICAL = "Chemical"
DISEASE = "Disease"
GENE = "Gene"
SPECIES = "Species"

ENTITY_TYPES = dict(
    Chemical=CHEMICAL,
    Disease=DISEASE,
    Gene=GENE,
    Species=SPECIES,
)


class TaggedEntity:
    def __init__(self, tag_tuple):
        self.document = int(tag_tuple[0])
        self.start = int(tag_tuple[1])
        self.end = int(tag_tuple[2])
        self.text = tag_tuple[3]
        self.type = ENTITY_TYPES[tag_tuple[4]]
        self.mesh = tag_tuple[5]

    def __str__(self):
        return "<Entity {},{},{},{},{}>".format(self.start, self.end, self.text, self.type, self.mesh)


class Sentence:
    def __init__(self, sid, text, start, end) -> None:
        super().__init__()
        self.start = start
        self.text = text
        self.sid = sid
        self.end = end


class TaggedDocument:
    REGEX_TITLE = re.compile("\|t\|(.*?)\n")
    REGEX_ABSTRACT = re.compile("\|a\|(.*?)\n")
    REGEX_TAGS = re.compile("(\d+)\t(\d+)\t(\d+)\t(.*?)\t(.*?)\t(.*?)\n")

    def __init__(self, pubtator_content):
        self.id = int(pubtator_content[:pubtator_content.index("|")])
        self.title = self.REGEX_TITLE.findall(pubtator_content)[0]
        self.abstract = self.REGEX_ABSTRACT.findall(pubtator_content)[0]
        self.content = self.title + self.abstract
        self.tags = [TaggedEntity(t) for t in self.REGEX_TAGS.findall(pubtator_content)]
        self.entity_names = {t.text.lower() for t in self.tags}
        # Indexes
        # self.mesh_by_entity_name = {}  # Use to select mesh descriptor by given entity
        self.sentence_by_id = {}  # Use to build mesh->sentence index
        self.entities_by_mesh = {}  # Use Mesh->TaggedEntity index to build Mesh->Sentence index
        self.sentences_by_mesh = {}  # Mesh->Sentence index
        self.entities_by_sentence = {}  # Use for _query processing
        self._create_index()

    def _create_index(self):
        # self.mesh_by_entity_name = {t.text.lower(): t.mesh for t in self.tags if
        #                            t.text.lower() not in self.mesh_by_entity_name}
        sentences = self.content.split(". ")
        for idx, sent in enumerate(sentences):
            self.sentence_by_id[idx] = Sentence(
                idx,
                sent.lower(),
                self.content.index(sent),
                self.content.index(sent) + len(sent),
            )

        for tag in self.tags:
            if tag.mesh not in self.entities_by_mesh:
                self.entities_by_mesh[tag.mesh] = []
            self.entities_by_mesh[tag.mesh] += [tag]

        for mesh, entities in self.entities_by_mesh.items():
            if mesh not in self.sentences_by_mesh:
                self.sentences_by_mesh[mesh] = set()
            for entity in entities:
                for sid, sent in self.sentence_by_id.items():
                    if sent.start <= entity.start <= sent.end:
                        self.sentences_by_mesh[mesh].add(sid)
                        if sid not in self.entities_by_sentence:
                            self.entities_by_sentence[sid] = set()
                        self.entities_by_sentence[sid].add(entity)
        pass

    def __str__(self):
        return "<Document {} {}>".format(self.id, self.title)
