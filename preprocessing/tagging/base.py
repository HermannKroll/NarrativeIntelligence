import logging
import os
import re
from threading import Thread

OUTPUT_INTERVAL = 30


class BaseTagger(Thread):
    OUTPUT_INTERVAL = 30

    def __init__(self, *args, root_dir=None, translation_dir=None, log_dir=None, config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_dir = root_dir
        self.translation_dir = translation_dir
        self.log_dir = log_dir
        self.config = config
        self.thread = None
        self.logger = logging.getLogger("preprocessing")
        self.name = self.__class__.__name__

    def prepare(self, resume=False):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def get_progress(self):
        raise NotImplementedError

    def finalize(self):
        raise NotImplementedError


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


def get_pmcid_from_filename(abs_path):
    filename = abs_path.split("/")[-1]
    return filename.split(".")[0]


def get_exception_causing_file_from_log(log_file):
    with open(log_file) as f_log:
        content = f_log.read()
    processed_files = re.findall(r"/.*?PMC\d+\.txt", content)
    if processed_files:
        return processed_files[-1]
    else:
        return None


def merge_result_files(translation_dir, output_file, *files):
    mentions_by_pmid = dict()
    for fn in files:
        with open(fn) as f:
            for line in f:
                if line.strip():
                    pmid = line.split("\t")[0]
                    if pmid not in mentions_by_pmid:
                        mentions_by_pmid[pmid] = set()
                    mentions_by_pmid[pmid].add(line)

    with open(output_file, "w") as f_out:
        for pmid, mentions in mentions_by_pmid.items():
            document_fn = os.path.join(translation_dir, "PMC{}.txt".format(pmid))
            if os.path.exists(document_fn):
                with open(document_fn) as f_doc:
                    f_out.write(f_doc.read().strip() + "\n")
                mention_list = sorted(mentions, key=lambda x: int(x.split("\t")[1]))
                f_out.writelines(mention_list)
                f_out.write("\n")
