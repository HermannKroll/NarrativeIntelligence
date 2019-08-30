import re


class TaggedEntity:
    def __init__(self, tuple):
        self.document = int(tuple[0])
        self.start = int(tuple[1])
        self.end = int(tuple[2])
        self.text = tuple[3]
        self.type = tuple[4]
        self.mesh = tuple[5]

    def __str__(self):
        return "<Entity {},{},{},{},{}>".format(self.start, self.end, self.text, self.type, self.mesh)


class TaggedDocument:
    REGEX_TITLE = re.compile("\|t\| (.*?)\n")
    REGEX_ABSTRACT = re.compile("\|a\| (.*?)\n")
    REGEX_TAGS = re.compile("(\d+)\t(\d+)\t(\d+)\t(.*?)\t(.*?)\t(.*?)\n")

    def __init__(self, pubtator_content):
        self.id = int(pubtator_content[:pubtator_content.index("|")])
        self.title = self.REGEX_TITLE.findall(pubtator_content)[0]
        self.abstract = self.REGEX_ABSTRACT.findall(pubtator_content)[0]
        self.content = self.title + self.abstract
        self.tags = [TaggedEntity(t) for t in self.REGEX_TAGS.findall(pubtator_content)]
        self.entities = {t.text for t in self.tags}

    def __str__(self):
        return "<Document {} {}>".format(self.id, self.title)