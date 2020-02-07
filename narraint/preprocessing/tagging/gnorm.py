import os
import re
import shutil
import subprocess
from datetime import datetime
from shutil import copyfile
from time import sleep

from narraint.backend import enttypes
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.pubtator.document import get_document_id


class GNorm(BaseTagger):
    TYPES = (enttypes.GENE,)
    __name__ = "GNormPlus"
    __version__ = "unknown"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "gnorm_in")
        self.out_dir = os.path.join(self.root_dir, "gnorm_out")
        self.log_file = os.path.join(self.log_dir, "gnorm.log")

    # TODO: Test if function works
    def get_exception_causing_file_from_log(self):
        with open(self.log_file) as f_log:
            content = f_log.read()
        processed_files = re.findall(r"/.*?\d+\.txt", content)
        if processed_files:
            return processed_files[-1]
        else:
            return None

    def prepare(self, resume=False):
        if not resume:
            os.mkdir(self.in_dir)
            for fn in self.files:
                target = os.path.join(self.in_dir, fn.split("/")[-1])
                shutil.copy(fn, target)
            os.mkdir(self.out_dir)
        else:
            self.logger.info("Resuming")

    def get_tags(self):
        return self._get_tags(self.out_dir)

    def run(self):
        """
        Method starts a GNormPlus instance with all files from ``in_dir`` and writes the result back to ``out_dir``.
        Log files are written into the directory ``log_dir``.

        If an error occurs during the execution of GNormPlus, the exit code is evaluated. If it's 1 the last processed
        file is removed and the instance is going to be restarted. If no file was processed the thread is cancelled and
        a manual analysis is recommended (maybe an OutOfMemoryException?).
        """
        skipped_files = []
        keep_tagging = True
        files_total = len(os.listdir(self.in_dir))
        start_time = datetime.now()

        while keep_tagging:
            with open(self.log_file, "w") as f_log:
                # Start GNormPlus
                sp_args = ["java", "-Xmx100G", "-Xms30G", "-jar", self.config.gnorm_jar, self.in_dir, self.out_dir,
                           self.config.gnorm_setup]
                process = subprocess.Popen(sp_args, cwd=self.config.gnorm_root, stdout=f_log, stderr=f_log)
                self.logger.debug("Starting {}".format(process.args))

                # Wait until finished
                while process.poll() is None:
                    sleep(self.OUTPUT_INTERVAL)
                    self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))
                self.logger.debug("Exited with code {}".format(process.poll()))

            if process.poll() == 1:
                # Java Exception
                last_file = self.get_exception_causing_file_from_log()
                if last_file:
                    last_id = get_document_id(last_file)
                    skipped_files.append(last_file)
                    self.logger.debug("Exception in file {}".format(last_file))
                    copyfile(self.log_file, "gnorm.{}.log".format(self.log_file, last_id))
                    os.remove(last_file)
                else:
                    # No file processed, assume another error
                    keep_tagging = False
                    self.logger.error("No files processed. Assuming an unexpected exception")
            else:
                keep_tagging = False

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(
            end_time - start_time,
            self.get_progress(),
            files_total,
            len(skipped_files)))

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
