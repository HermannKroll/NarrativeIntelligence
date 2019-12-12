import logging
import os
import re
from threading import Thread

from narraint.backend.database import Session
from narraint.backend.models import Tag

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


# TODO: Remove in future versions
def finalize_dir(files_dir, result_file, batch_mode=False, keep_incomplete_lines=False):
    file_list = sorted(os.path.join(files_dir, fn) for fn in os.listdir(files_dir) if fn.endswith(".txt"))
    with open(result_file, "w") as f_out:
        for fn in file_list:
            if batch_mode:
                content = []
                with open(fn) as f_in:
                    documents = f_in.read().strip().split("\n\n")
                for doc in documents:
                    doc_content = doc.strip().split("\n")
                    content += doc_content[2:]
            else:
                with open(fn) as f_in:
                    content = f_in.read().strip().split("\n")
                content = content[2:]
            # Write to file
            f_out.writelines(line + "\n" for line in content if line.count("\t") == 5 or keep_incomplete_lines)


def get_exception_causing_file_from_log(log_file):
    with open(log_file) as f_log:
        content = f_log.read()
    processed_files = re.findall(r"/.*?PMC\d+\.txt", content)
    if processed_files:
        return processed_files[-1]
    else:
        return None
