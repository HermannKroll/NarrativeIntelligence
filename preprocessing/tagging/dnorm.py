import os
import subprocess
from datetime import datetime
from time import sleep

from tagging.base import BaseTagger
from tools import concat, count_documents


class DNorm(BaseTagger):
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
        self.logger.info("Finished in {} ({} files total, {} errors)".format(
            end_time - start_time,
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
