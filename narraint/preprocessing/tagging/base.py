import logging
import os
from threading import Thread

from narraint.backend.database import Session
from narraint.backend.models import Tag
from narraint.pubtator.regex import TAG_LINE_NORMAL

OUTPUT_INTERVAL = 30


class BaseTagger(Thread):
    OUTPUT_INTERVAL = 30
    TYPES = None
    __version__ = None

    def __init__(self, *args, collection=None, root_dir=None, input_dir=None, log_dir=None, config=None,
                 file_mapping=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = collection
        self.root_dir = root_dir
        self.input_dir = input_dir
        self.log_dir = log_dir
        self.config = config
        self.thread = None
        self.logger = logging.getLogger("preprocessing")
        self.name = self.__class__.__name__
        self.files = set()
        self.file_mapping = file_mapping

    def add_files(self, *files):
        self.files.update(files)

    def prepare(self, resume=False):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def get_progress(self):
        raise NotImplementedError

    def finalize(self):
        session = Session.get()
        tags = set(self.get_tags())
        tags_cleaned = tags.copy()
        for tag1 in tags:
            for tag2 in tags_cleaned:
                if int(tag2[1]) < int(tag1[1]) and int(tag2[2]) > int(tag1[2]):
                    tags_cleaned.remove(tag1)
                    break

        for tag in tags_cleaned:
            session.add(Tag(
                start=tag[1],
                end=tag[2],
                type=tag[4],
                ent_str=tag[3],
                ent_id=tag[5],
                document_id=tag[0],
                document_collection=self.collection,
                tagger="{}/{}".format(self.name, self.__version__),
            ))
        session.commit()

    def get_tags(self):
        """
        Function returns list of 6-tuples with tags.
        Tuple consists of (document ID, start pos., end pos., matched text, tag type, entity ID)
        :return: List of 6-tuples
        """
        raise NotImplementedError

    @staticmethod
    def _get_tags(directory):
        tags = []
        for fn in os.listdir(directory):
            with open(os.path.join(directory, fn)) as f:
                tags.extend(TAG_LINE_NORMAL.findall(f.read()))
        return tags
