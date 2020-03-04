import logging
import os
from threading import Thread
from typing import List, Tuple, Dict, Set

from sqlalchemy.dialects.postgresql import insert

from narraint.backend.database import Session
from narraint.backend.load import insert_taggers
from narraint.backend.models import Tag, DocTaggedBy
from narraint.preprocessing.config import Config
from narraint.pubtator.regex import TAG_LINE_NORMAL


# TODO: Add estimation when tagging is done
class BaseTagger(Thread):
    """
    Tagger base class. Provides basic functionality like
    - the initialization of logging,
    - adding tags to the database
    - selecting all tags which were found
    """
    OUTPUT_INTERVAL = 30
    TYPES = None
    __name__ = None
    __version__ = None

    def __init__(
            self, *args,
            collection: str = None,
            root_dir: str = None,
            input_dir: str = None,
            log_dir: str = None,
            config: Config = None,
            mapping_id_file: Dict[int, str] = None,
            mapping_file_id: Dict[str, int] = None,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.collection: str = collection
        self.root_dir: str = root_dir
        self.input_dir: str = input_dir
        self.log_dir: str = log_dir
        self.config: Config = config
        self.thread = None
        self.logger = logging.getLogger("preprocessing")
        self.name = self.__class__.__name__
        self.files = set()
        self.mapping_id_file: Dict[int, str] = mapping_id_file
        self.mapping_file_id: Dict[str, int] = mapping_file_id
        self.id_set: Set[int] = set()

    def add_files(self, *files: str):
        self.files.update(files)
        self.id_set.update(self.mapping_file_id[fn] for fn in files)

    def prepare(self, resume=False):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def get_progress(self):
        raise NotImplementedError

    def finalize(self):
        """
        Add tags into database. First, clean tags, i.e., remove smaller tag ranges which are included in a larger tag.
        Create a mapping from document ID to set of tags and clean each set.

        Then, add tags into the database.
        """
        session = Session.get()
        tags = set(self.get_tags())

        self.logger.info('Cleaning tags')
        # Clean tags (remove smaller tags which are included in larger tags)
        doc2tags = {}
        for t in tags:
            did = t[0]
            if did not in doc2tags:
                doc2tags[did] = []
            doc2tags[did].append(t)

        # compare just the tags within a document
        tags_cleaned = []
        for did, doc_tags in doc2tags.items():
            doc_tags_cleaned = doc_tags.copy()
            for t1 in doc_tags:
                for t2 in doc_tags_cleaned:
                    if int(t2[1]) < int(t1[1]) and int(t2[2]) > int(t1[2]):
                        doc_tags_cleaned.remove(t1)
                        break
            tags_cleaned.extend(doc_tags_cleaned)

        self.logger.info('Add tagger')
        tagger_name = self.__name__
        tagger_version = self.__version__
        insert_taggers((tagger_name, tagger_version))

        self.logger.info("Add tags")
        for d_id, start, end, ent_str, ent_type, ent_id in tags_cleaned:
            insert_tag = insert(Tag).values(
                ent_type=ent_type,
                start=start,
                end=end,
                ent_id=ent_id,
                ent_str=ent_str,
                document_id=d_id,
                document_collection=self.collection,
                tagger_name=tagger_name,
                tagger_version=tagger_version,
            ).on_conflict_do_nothing(
                index_elements=('document_id', 'document_collection', 'start', 'end', 'ent_type', 'ent_id'),
            )
            session.execute(insert_tag)
            session.commit()

        self.logger.info("Add doc_tagged_by")
        processed_ent_types = set((did, ent_type) for ent_type in self.TYPES for did in self.id_set)
        for did, ent_type in processed_ent_types:
            insert_doc_tagged_by = insert(DocTaggedBy).values(
                document_id=did,
                document_collection=self.collection,
                tagger_name=tagger_name,
                tagger_version=tagger_version,
                ent_type=ent_type,
            ).on_conflict_do_nothing(
                index_elements=('document_id', 'document_collection',
                                'tagger_name', 'tagger_version', 'ent_type'),
            )
            session.execute(insert_doc_tagged_by)
            session.commit()

        self.logger.info("Committed successfully")

    def get_tags(self):
        """
        Function returns list of 6-tuples with tags.
        Tuple consists of (document ID, start pos., end pos., matched text, tag type, entity ID)
        :return: List of 6-tuples
        """
        raise NotImplementedError

    @staticmethod
    def _get_tags(directory: str) -> List[Tuple[int, int, int, str, str, str]]:
        """
        Function returns list of tags (6-tuples) contained in all files in a certain directory.

        :param directory: Path to directory containing PubTator files
        :return: List of tag-tuples
        """
        tags = []
        # TODO: This function could (!) be too memory-intensive
        for fn in os.listdir(directory):
            with open(os.path.join(directory, fn)) as f:
                tags.extend(TAG_LINE_NORMAL.findall(f.read()))
        return tags
