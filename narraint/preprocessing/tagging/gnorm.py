import os
import shutil
import subprocess
from datetime import datetime
from shutil import copyfile
from time import sleep

from narraint.backend import types
from narraint.preprocessing.tagging.base import BaseTagger, get_pmcid_from_filename, \
    get_exception_causing_file_from_log, \
    finalize_dir


# FIXME: Adapt to new API
class GNorm(BaseTagger):
    TYPES = (types.GENE,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "gnorm_in")
        self.out_dir = os.path.join(self.root_dir, "gnorm_out")
        self.result_file = os.path.join(self.root_dir, "genes.txt")
        self.log_file = os.path.join(self.log_dir, "gnorm.log")

    def prepare(self, resume=False):
        if not resume:
            shutil.copytree(self.input_dir, self.in_dir)
            os.mkdir(self.out_dir)
        else:
            self.logger.info("Resuming")

    def finalize(self):
        finalize_dir(self.out_dir, self.result_file)

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
                last_file = get_exception_causing_file_from_log(self.log_file)
                if last_file:
                    last_pmcid = get_pmcid_from_filename(last_file)
                    skipped_files.append(last_file)
                    self.logger.debug("Exception in file {}".format(last_file))
                    copyfile(self.log_file, "gnorm.{}.log".format(self.log_file, last_pmcid))
                    os.remove(last_file)
                else:
                    # No file processed, assume another error
                    keep_tagging = False
                    self.logger.error("No files processed. Assuming an unexpected exception")
            else:
                keep_tagging = False

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(end_time - start_time,
                                                                                                 self.get_progress(),
                                                                                                 files_total,
                                                                                                 len(skipped_files)))

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
