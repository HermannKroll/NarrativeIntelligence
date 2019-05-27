import os
import shutil
import subprocess
from datetime import datetime
from time import sleep

from tagging.base import BaseTagger


class TMChem(BaseTagger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "tchem_in")
        self.out_dir = os.path.join(self.root_dir, "tchem_out")
        self.result_file = os.path.join(self.root_dir, "chemicals.txt")
        self.log_file = os.path.join(self.log_dir, "tchem.log")

    def prepare(self, resume=False):
        if not resume:
            shutil.copytree(self.translation_dir, self.in_dir)
            os.mkdir(self.out_dir)

    def run(self):
        # skipped_files = []
        latest_exit_code = 1
        files_total = len(os.listdir(self.in_dir))
        start_time = datetime.now()

        while latest_exit_code == 1:
            with open(self.log_file, "w") as f_log:
                sp_args = ["/bin/bash", "-c", "{} {} {}".format(self.config.tmchem_script, self.in_dir, self.out_dir)]
                process = subprocess.Popen(sp_args, cwd=self.config.tmchem_root, stdout=f_log, stderr=f_log)
                self.logger.debug("Starting {}".format(process.args))

                # Wait until finished
                while process.poll() is None:
                    sleep(self.OUTPUT_INTERVAL)
                    self.logger.info("Progress {}/{}".format(self.get_progress(), files_total))
                self.logger.debug("Exited with code {}".format(process.poll()))
                latest_exit_code = process.poll()

            # if process.poll() == 1:
            #     # Java Exception
            #     with open(self.log_file) as f_log:
            #         content = f_log.read()
            #     matches = re.findall(r"/.*?PMC\d+\.txt", content)
            #     if matches:
            #         last_file = matches[-1]
            #         skipped_files.append(last_file)
            #         self.logger.debug("GNormPlus exception in file {}".format(last_file))
            #         copyfile(self.log_file, "{}.{}".format(self.log_file, len(skipped_files)))
            #         os.remove(last_file)
            #         latest_exit_code = process.poll()
            #     else:
            #         # No file processed, assume another error
            #         latest_exit_code = None
            #         self.logger.error("No files processed. Assuming an unexpected exception")

        end_time = datetime.now()
        self.logger.info(
            "Finished in {} ({} files processed, {} files total)".format(end_time - start_time, self.get_progress(),
                                                                         files_total))

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
