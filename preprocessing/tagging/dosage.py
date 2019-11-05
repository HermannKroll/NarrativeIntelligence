import os
import re
import shutil
from datetime import datetime

from mesh.data import MeSHDB
from tagging.base import BaseTagger, finalize_dir


class DocumentError(Exception):
    pass


class DosageFormTagger(BaseTagger):
    DOSAGE_FORM_ID = "D004304"
    DOSAGE_FORM_TREE_NUMBER = "D26.255"
    TYPE = "DosageForm"
    MESH_FILE = "../data/desc2020.xml"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "dosage_in")
        self.out_dir = os.path.join(self.root_dir, "dosage_out")
        self.result_file = os.path.join(self.root_dir, "dosage.txt")
        self.log_file = os.path.join(self.log_dir, "dosage.log")
        self.meshdb = None
        self.desc_by_term = {}
        self.regex = re.compile(r"^(\d+)\|t\|\s(.*?)\n\d+\|a\|\s(.*?)$")

    def prepare(self, resume=False):
        self.meshdb = MeSHDB.instance()
        self.meshdb.load_xml(self.MESH_FILE)
        dosage_forms = self.meshdb.descs_under_tree_number(self.DOSAGE_FORM_TREE_NUMBER)
        for dosage_form in dosage_forms:
            for term in dosage_form.terms:
                if term.string.lower() in self.desc_by_term:
                    raise ValueError("Term duplicate found")
                self.desc_by_term[term.string.lower()] = dosage_form.unique_id

        if not resume:
            shutil.copytree(self.translation_dir, self.in_dir)
            os.mkdir(self.out_dir)
        else:
            raise NotImplementedError

    def finalize(self):
        finalize_dir(self.out_dir, self.result_file)

    def run(self):
        skipped_files = []
        files_total = len(os.listdir(self.in_dir))
        start_time = datetime.now()

        for fn in os.listdir(self.in_dir):
            if fn.startswith("PMC") and fn.endswith(".txt"):
                in_file = os.path.join(self.in_dir, fn)
                out_file = os.path.join(self.out_dir, fn)
                try:
                    self.tag(in_file, out_file)
                except DocumentError:
                    skipped_files.append(in_file)
                    self.logger.info("DocumentError for {}".format(in_file))
                os.remove(in_file)
                self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(end_time - start_time,
                                                                                                 self.get_progress(),
                                                                                                 files_total,
                                                                                                 len(skipped_files)))

    def tag(self, in_file, out_file):
        with open(in_file) as f:
            document = f.read()
        match = self.regex.match(document.strip())
        if not match:
            raise DocumentError
        pmid, title, abstact = match.group(1, 2, 3)
        content = title + abstact
        content = content.lower()

        # Generate output
        output = document.strip() + "\n"
        for term, desc in self.desc_by_term.items():
            for match in re.finditer(term, content):
                start = match.start()
                end = match.end()
                # Find left end of sequence sequence
                try:
                    idx = content.rindex(" ", 0, start)
                    if idx != start - 1:
                        start = idx + 1
                except ValueError:
                    start = 0
                # Find right end of sequence sequence
                try:
                    idx = content.index(" ", end)
                    if idx > end:
                        end = idx
                except ValueError:
                    end = len(content) - 1

                occurrence = content[start:end]
                occurrence = occurrence.rstrip(".,;")

                line = "{id}\t{start}\t{end}\t{str}\t{type}\tMESH:{desc}\n".format(
                    id=pmid, start=start, end=start + len(occurrence), str=occurrence, type=self.TYPE, desc=desc
                )
                output += line
        output += "\n"

        # Write
        with open(out_file, "w") as f:
            f.write(output)

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
