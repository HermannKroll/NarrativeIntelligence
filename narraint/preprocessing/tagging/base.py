import logging
import os
from threading import Thread

from narraint.backend.database import Session
from narraint.backend.models import Tag, ProcessedFor
from narraint.pubtator.regex import TAG_LINE_NORMAL


class BaseTagger(Thread):
    OUTPUT_INTERVAL = 30
    TYPES = None
    __version__ = None

    def __init__(self, *args, collection=None, root_dir=None, input_dir=None, log_dir=None, config=None,
                 mapping_id_file=None, mapping_file_id=None, **kwargs):
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
        self.mapping_id_file = mapping_id_file
        self.mapping_file_id = mapping_file_id
        self.id_set = set()

    def add_files(self, *files):
        self.files.update(files)
        self.id_set.update(self.mapping_file_id[fn] for fn in files)

    def prepare(self, resume=False):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def get_progress(self):
        raise NotImplementedError

    def finalize(self):
        session = Session.get()
        tags = set(self.get_tags())

        self.logger.info('cleaning tags...')
        # clean tags (remove smaller tags which are included in larger tags)
        # we do this document wise now
        # create a dict and map tags to their documents
        doc2tags = {}
        for t in tags:
            did = t[0]
            if did not in doc2tags:
                doc2tags[did] = [t]
            else:
                doc2tags[did].append(t)

        tags_cleaned = []
        # go through all tags in each doc
        for did, doc_tags in doc2tags.items():
            # create a copy of tags and clean it
            doc_tags_cleaned = list(doc_tags).copy()
            for t1 in doc_tags:
                for t2 in doc_tags_cleaned:
                    if int(t2[1]) < int(t1[1]) and int(t2[2]) > int(t1[2]):
                        doc_tags_cleaned.remove(t1)
                        break
            # append only the cleaned tags
            tags_cleaned.extend(doc_tags_cleaned)

        self.logger.info('preparing commit...')
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

        self.logger.info('locking table processed_for')
        # Add processed documents
        Session.lock_tables("processed_for")
        processed = set((did, self.collection, ent_type) for ent_type in self.TYPES for did in self.id_set)
        processed_db = set(
            session.query(ProcessedFor).filter(ProcessedFor.document_collection == self.collection).values(
                ProcessedFor.document_id, ProcessedFor.document_collection, ProcessedFor.ent_type
            )
        )
        processed_missing = processed.difference(processed_db)
        for doc_id, doc_collection, ent_type in processed_missing:
            session.add(ProcessedFor(
                document_id=doc_id,
                document_collection=self.collection,
                ent_type=ent_type,
            ))

        # Commit
        session.commit()
        self.logger.info("process for committed")

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
