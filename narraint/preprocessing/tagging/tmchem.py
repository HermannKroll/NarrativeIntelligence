import os
import shutil
import subprocess
from datetime import datetime
from time import sleep

from narraint.backend import types
from narraint.preprocessing.tagging.base import BaseTagger, finalize_dir

# FIXME: Adapt to new API
class TMChem(BaseTagger):
    TYPES = (types.CHEMICAL,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "tchem_in")
        self.out_dir = os.path.join(self.root_dir, "tchem_out")
        self.result_file = os.path.join(self.root_dir, "chemicals.txt")
        self.log_file = os.path.join(self.log_dir, "tchem.log")

    def prepare(self, resume=False):
        if not resume:
            shutil.copytree(self.input_dir, self.in_dir)
            os.mkdir(self.out_dir)
        else:
            self.logger.info("Resuming")

    def run(self):
        files_total = len(os.listdir(self.in_dir))
        start_time = datetime.now()

        with open(self.log_file, "w") as f_log:
            sp_args = ["/bin/bash", "-c", "{} {} {}".format(self.config.tmchem_script, self.in_dir, self.out_dir)]
            process = subprocess.Popen(sp_args, cwd=self.config.tmchem_root, stdout=f_log, stderr=f_log)
            self.logger.debug("Starting {}".format(process.args))

            # Wait until finished
            while process.poll() is None:
                sleep(self.OUTPUT_INTERVAL)
                self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))
            self.logger.debug("Exited with code {}".format(process.poll()))

            # Problem:
            # Automatically resuming tmChem is not as easy as it looks because the application does not log which
            # file it is processing. So the error-causing file can't be found so easily

        end_time = datetime.now()
        self.logger.info(
            "Finished in {} ({} files processed, {} files total)".format(end_time - start_time, self.get_progress(),
                                                                         files_total))

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])

    def finalize(self):
        finalize_dir(self.out_dir, self.result_file)
