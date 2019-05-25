import os
import shutil

from tagging.base import BaseTagger


class TChem(BaseTagger):
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
        raise NotImplementedError

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])
