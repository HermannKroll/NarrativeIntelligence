import os
import re
import subprocess
from datetime import datetime
from time import sleep

from narraint.backend import types
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.pubtator.count import count_documents


class DNorm(BaseTagger):
    """
    DNorm is a diseases tagger.

    Input: Single with with all documents. Similar to PubTator format except that the |t| and |a| are replaced
    by an tab, so a line is <id>\t<content>.

    Output: Single file with tags. Each line represents a tag consisting of five elements, which are separated by a tab.
        Line format: <doc id> <start> <end> <string> <entity id>

    .. note:

       Output format does not include the type of the tag, i.e., disease
    """
    TYPES = (types.DISEASE,)
    __version__ = "0.0.7"

    def get_document_info(self, doc_id):
        with open(self.mapping_id_file[doc_id]) as f:
            content = f.readlines()
        title = re.sub(r"\d+\|t\|", "", content[0]).strip()
        abstract = re.sub(r"\d+\|a\|", "", content[1]).strip()
        return title + abstract, len(title)

    def get_tags(self):
        tags = []
        documents = {}
        if os.path.exists(self.out_file):
            with open(self.out_file) as f:
                for line in f:
                    if line.strip():
                        new_line = line.strip().split("\t")
                        # Add type
                        if len(new_line) == 4 or len(new_line) == 5:
                            new_line.insert(4, types.DISEASE)
                        if len(new_line) == 4:
                            new_line.insert(5, "")
                        # Read source document
                        doc_id = int(new_line[0])
                        if doc_id not in documents:
                            documents[doc_id] = self.get_document_info(doc_id)
                        # Perform indexing check
                        document, title_len = documents[doc_id]
                        if document[int(new_line[1]):int(new_line[2])] != new_line[3]:
                            idx_left = int(new_line[1]) + title_len
                            idx_right = int(new_line[2]) + title_len
                            new_line[1] = str(idx_left)
                            new_line[2] = str(idx_right)
                        # Write result
                        tags.append(new_line)
        return tags

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_file = os.path.join(self.log_dir, "dnorm.log")
        self.in_file = os.path.join(self.root_dir, "dnorm_in.txt")
        self.out_file = os.path.join(self.root_dir, "dnorm_out.txt")

    def prepare(self, resume=False):
        if not resume:
            with open(self.in_file, "w") as f_out:
                for fn in self.files:
                    with open(fn) as f_in:
                        content = f_in.read()
                    content = content.replace("|t| ", "\t")
                    content = content.replace("|a| ", "\t")
                    f_out.write(content)
        else:
            # Here you must get the already processed IDs and create a new file with all the missing IDs.
            # You must rename the old output file and make sure its not overwritten
            raise NotImplementedError("Resuming DNorm is not implemented.")

    def run(self):
        files_total = len(os.listdir(self.input_dir))
        start_time = datetime.now()

        with open(self.log_file, "w") as f_log:
            command = "{} {} {} {} {} {}".format(
                self.config.dnorm_script, self.config.dnorm_config, self.config.dnorm_lexicon, self.config.dnorm_matrix,
                self.in_file, self.out_file)
            sp_args = ["/bin/bash", "-c", command]
            process = subprocess.Popen(sp_args, cwd=self.config.dnorm_root, stdout=f_log, stderr=f_log)
        self.logger.debug("Starting {}".format(process.args))

        # Wait until finished
        while process.poll() is None:
            sleep(self.OUTPUT_INTERVAL)
            self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))
        self.logger.debug("Exited with code {}".format(process.poll()))

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(
            end_time - start_time,
            self.get_progress(),
            files_total,
            self.count_skipped_files()),
        )

    def get_progress(self):
        return count_documents(self.out_file) if os.path.exists(self.out_file) else 0

    def count_skipped_files(self):
        with open(self.log_file) as f:
            content = f.read()
        return content.count("WARNING:")
