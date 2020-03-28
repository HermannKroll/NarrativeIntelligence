import os
import shutil
import subprocess
from datetime import datetime
from time import sleep

from narraint.entity import enttypes
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.progress import print_progress_with_eta


class TMChem(BaseTagger):
    TYPES = (enttypes.CHEMICAL,)
    __name__ = "tmChem"
    __version__ = "0.0.2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "tmchem_in")
        self.out_dir = os.path.join(self.root_dir, "tmchem_out")
        self.log_file = os.path.join(self.log_dir, "tmchem.log")

    def prepare(self, resume=False):
        if not resume:
            os.mkdir(self.in_dir)
            for fn in self.files:
                target = os.path.join(self.in_dir, fn.split("/")[-1])
                shutil.copy(fn, target)
            os.mkdir(self.out_dir)
        else:
            self.logger.info("Resuming")

    def run(self):
        files_total = len(os.listdir(self.in_dir))
        start_time = datetime.now()

        with open(self.log_file, "w") as f_log:
            sp_args = ["/bin/bash", "-c", "{} {} {}".format(
                self.config.tmchem_script,
                self.in_dir,
                self.out_dir)]
            process = subprocess.Popen(sp_args, cwd=self.config.tmchem_root, stdout=f_log, stderr=f_log)
            self.logger.debug("Starting {}".format(process.args))

            # Wait until finished
            done = False
            while not done:
                sleep(self.OUTPUT_INTERVAL)
                progress = self.get_progress()
                print_progress_with_eta("tmChem tagging", progress-1 if progress > 0 else 0, files_total, start_time,
                                        print_every_k=1, logger=self.logger)
                if progress >= files_total:
                    lastline = get_last_line(self.log_file)
                    done = lastline == b'Waiting for input\n' #hacky, might break in the next tmchem version
            self.logger.debug("Terminating tmChem tagger")
            process.terminate()

            # Problem:
            # Automatically resuming tmChem is not as easy as it looks because the application does not log which
            # file it is processing. So the error-causing file can't be found so easily

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total)".format(
            end_time - start_time,
            self.get_progress(),
            files_total))

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])

    def get_tags(self):
        return self._get_tags(self.out_dir)

def get_last_line(logfile):
    with open(logfile, "rb") as f:
        first = f.readline()  # Read the first line.
        f.seek(-2, os.SEEK_END)  # Jump to the second last byte.
        while f.read(1) != b"\n":  # Until EOL is found...
            f.seek(-2, os.SEEK_CUR)  # ...jump back the read byte plus one more.
        return f.readline()
