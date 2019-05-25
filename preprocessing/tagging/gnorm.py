import os
import re
import shutil
import subprocess
from datetime import datetime
from shutil import copyfile
from time import sleep

from tagging.base import BaseTagger


class GNorm(BaseTagger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "gnorm_in")
        self.out_dir = os.path.join(self.root_dir, "gnorm_out")
        self.result_file = os.path.join(self.root_dir, "genes.txt")
        self.log_file = os.path.join(self.log_dir, "gnorm.log")

    def prepare(self, resume=False):
        if not resume:
            shutil.copytree(self.translation_dir, self.in_dir)
            os.mkdir(self.out_dir)

    def run(self):
        """
        Method starts a GNormPlus instance with all files from ``in_dir`` and writes the result back to ``out_dir``.
        Log files are written into the directory ``log_dir``.

        If an error occurs during the execution of GNormPlus, the exit code is evaluated. If it's 1 the last processed
        file is removed and the instance is going to be restarted. If no file was processed the thread is cancelled and
        a manual analysis is recommended (maybe an OutOfMemoryException?).
        """
        skipped_files = []
        latest_exit_code = 1
        files_total = len(os.listdir(self.in_dir))
        start_time = datetime.now()

        while latest_exit_code == 1:
            with open(self.log_file, "w") as f_log:
                # Start GNormPlus
                sp_args = ["java", "-Xmx100G", "-Xms30G", "-jar", self.config.gnorm_jar, self.in_dir, self.out_dir,
                           self.config.gnorm_setup]
                process = subprocess.Popen(sp_args, cwd=self.config.gnorm_root, stdout=f_log, stderr=f_log)
                self.logger.debug("Starting GNormPlus {}".format(process.args))

                # Wait until finished
                while process.poll() is None:
                    sleep(self.OUTPUT_INTERVAL)
                    self.logger.info("GNormPlus progress {}/{}".format(self.get_progress(), files_total))
                self.logger.debug("GNormPlus exited with code {}".format(process.poll()))
                latest_exit_code = process.poll()

            if process.poll() == 1:
                # Remove problematic document
                with open(self.log_file) as f_log:
                    content = f_log.read()
                matches = re.findall(r"/.*?PMC\d+\.txt", content)
                if matches:
                    last_file = matches[-1]
                    skipped_files.append(last_file)
                    self.logger.debug("GNormPlus exception in file {}".format(last_file))
                    copyfile(self.log_file, "{}.{}".format(self.log_file, len(skipped_files)))
                    os.remove(last_file)  # TODO:Fix
                    latest_exit_code = process.poll()
                else:
                    # No file processed, assume another error
                    latest_exit_code = None
                    self.logger.error("No files processed. Assuming an unexpected exception")

        end_time = datetime.now()
        self.logger.info("GNormPlus finished in {} ({} files total, {} errors)".format(end_time - start_time,
                                                                                       files_total,
                                                                                       len(skipped_files)))

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
