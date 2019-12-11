import os
import re
from datetime import datetime

from narraint import config
from narraint.backend import types
from narraint.pubtator.regex import TAG_LINE_NORMAL, CONTENT_ID_TIT_ABS
from narraint.mesh.data import MeSHDB
from narraint.preprocessing.tagging.base import BaseTagger


class DocumentError(Exception):
    pass


class DosageFormTagger(BaseTagger):
    DOSAGE_FORM_TREE_NUMBERS = (
        "D26.255",  # Dosage Forms
        "E02.319.300",  # Drug Delivery Systems
        "J01.637.512.600",  # Nanoparticles
        "J01.637.512.850",  # Nanotubes
        "J01.637.512.925",  # Nanowires
    )
    TYPES = (types.DOSAGE_FORM,)
    __version__ = "1.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "dosage_in")
        self.out_dir = os.path.join(self.root_dir, "dosage_out")
        self.result_file = os.path.join(self.root_dir, "dosage.txt")
        self.log_file = os.path.join(self.log_dir, "dosage.log")
        self.meshdb = None
        self.desc_by_term = {}

    def prepare(self, resume=False):
        self.meshdb = MeSHDB.instance()
        self.meshdb.load_xml(config.MESH_DESCRIPTORS_FILE)

        for df_tn in self.DOSAGE_FORM_TREE_NUMBERS:
            dosage_form_header_node = self.meshdb.desc_by_tree_number(df_tn)
            dosage_forms = self.meshdb.descs_under_tree_number(df_tn)
            dosage_forms.append(dosage_form_header_node)
            for dosage_form in dosage_forms:
                # add all terms for desc
                terms = []
                for t in dosage_form.terms:
                    # e.g. tag ointments as well as ointment (plural form -> singular form)
                    if t.string.endswith('s'):
                        # convert to singular
                        terms.append(t.string[0:-1].lower())
                    else:
                        # add plural form
                        terms.append(t.string.lower() + 's')
                    terms.append(t.string.lower())
                # go trough heading and all terms
                for term in terms:
                    if term in self.desc_by_term:
                        current_desc = self.desc_by_term[term]
                        if current_desc != dosage_form.unique_id:
                            raise ValueError(
                                "Term duplicate found {} with different descriptors ({} vs {})".format(term,
                                                                                                       current_desc,
                                                                                                       dosage_form.unique_id))
                        else:
                            continue
                    self.desc_by_term[term] = dosage_form.unique_id
        # Create output directory
        if not resume:
            os.mkdir(self.out_dir)
        else:
            raise NotImplementedError("Resuming DosageFormTagger is not implemented.")

    def get_tags(self):
        tags = []
        for fn in os.listdir(self.out_dir):
            with open(os.path.join(self.out_dir, fn)) as f:
                tags.extend(TAG_LINE_NORMAL.findall(f.read()))
        return tags

    def run(self):
        skipped_files = []
        files_total = len(self.files)
        start_time = datetime.now()

        for in_file in self.files:
            if in_file.endswith(".txt"):
                out_file = os.path.join(self.out_dir, in_file.split("/")[-1])
                try:
                    self.tag(in_file, out_file)
                except DocumentError:
                    skipped_files.append(in_file)
                    self.logger.info("DocumentError for {}".format(in_file))
                self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))
            else:
                self.logger.debug("Ignoring {}: Suffix .txt missing".format(in_file))

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(
            end_time - start_time,
            self.get_progress(),
            files_total,
            len(skipped_files)),
        )

    def tag(self, in_file, out_file):
        with open(in_file) as f:
            document = f.read()
        match = CONTENT_ID_TIT_ABS.match(document)
        if not match:
            raise DocumentError
        pmid, title, abstact = match.group(1, 2, 3)
        content = title.strip() + " " + abstact.strip()
        content = content.lower()

        # Generate output
        output = ""
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
                    id=pmid, start=start, end=start + len(occurrence), str=occurrence, type=types.DOSAGE_FORM, desc=desc
                )
                output += line

        # Write
        with open(out_file, "w") as f:
            f.write(output)

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
