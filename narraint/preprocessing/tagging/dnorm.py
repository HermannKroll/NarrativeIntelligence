import os
import re
import subprocess
from datetime import datetime
from time import sleep

from narraint.preprocessing.tagging.base import BaseTagger
from narraint.preprocessing.tools import concat, count_documents


class DNorm(BaseTagger):
    def get_document_dict(self, pmid):
        with open(os.path.join(self.translation_dir, "PMC{}.txt".format(pmid))) as f:
            content = f.readlines()
        title = re.sub(r"\d+\|t\| ", "", content[0]).rstrip("\n")
        abstract = re.sub(r"\d+\|a\| ", "", content[1]).rstrip("\n")
        return dict(
            doc=title + abstract,
            title_len=len(title),
        )

    def finalize(self):
        documents = dict()
        with open(self.out_file) as f:
            content = f.readlines()
        with open(self.result_file, "w") as f_out:
            for line in content:
                if line.strip():
                    new_line = line.strip().split("\t")
                    # Add type
                    if len(new_line) == 4 or len(new_line) == 5:
                        new_line.insert(4, "Disease")
                    if len(new_line) == 4:
                        new_line.insert(5, "")
                    # Read source document
                    if new_line[0] not in documents:
                        documents[new_line[0]] = self.get_document_dict(new_line[0])
                    # Perform indexing check
                    doc = documents[new_line[0]]["doc"]
                    if doc[int(new_line[1]):int(new_line[2])] != new_line[3]:
                        title_len = documents[new_line[0]]["title_len"]
                        idx_left = int(new_line[1]) + title_len
                        idx_right = int(new_line[2]) + title_len
                        new_line[1] = str(idx_left)
                        new_line[2] = str(idx_right)
                    # Write result
                    f_out.write("\t".join(new_line) + "\n")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "dnorm_in")
        self.out_dir = os.path.join(self.root_dir, "dnorm_out")
        self.result_file = os.path.join(self.root_dir, "diseases.txt")
        self.log_file = os.path.join(self.log_dir, "dnorm.log")
        self.in_file = os.path.join(self.in_dir, "dnorm_in.txt")
        self.out_file = os.path.join(self.out_dir, "dnorm_out.txt")

    def prepare(self, resume=False):
        if not resume:
            os.mkdir(self.in_dir)
            os.mkdir(self.out_dir)
            concat(self.translation_dir, self.in_file)
            with open(self.in_file) as f:
                content = f.read()
            content = content.replace("|t| ", "\t")
            content = content.replace("|a| ", "\t")
            with open(self.in_file, "w") as f:
                f.write(content)
        else:
            # Here you must get the already processed IDs and create a new batch file with all the missing IDs.
            # You must rename the old output file and make sure its not overwritten
            raise NotImplementedError("Resuming DNorm is not implemented.")

    def run(self):
        files_total = len(os.listdir(self.translation_dir))
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
        if os.path.exists(self.out_file):
            return count_documents(self.out_file)
        else:
            return 0

    def count_skipped_files(self):
        with open(self.log_file) as f:
            content = f.read()
        return content.count("WARNING:")
