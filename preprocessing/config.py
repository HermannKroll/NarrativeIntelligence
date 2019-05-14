import json
import os


# TODO: Add doc
class Config:
    def __init__(self, config_file):
        with open(config_file) as f:
            self.config = json.load(f)
        # Validate
        if not os.path.exists(self.pmc_dir) or not os.path.isdir(self.pmc_dir):
            raise ValueError(f"PubMedCentral directory not found: {self.pmc_dir} does not exist or is not a directory")

    @property
    def pmc_dir(self):
        return self.config["pmc_dir"]

    @property
    def tagger_one_root(self):
        return self.config["taggerOne"]["root"]

    @property
    def tagger_one_model(self):
        return os.path.join(self.tagger_one_root, self.config["taggerOne"]["model"])

    @property
    def tagger_one_script(self):
        return os.path.join(self.tagger_one_root, "ProcessText.sh")

    @property
    def tagger_one_batch_size(self):
        return int(self.config["taggerOne"]["batchSize"])

    @property
    def gnorm_root(self):
        return self.config["gnormPlus"]

    @property
    def gnorm_setup(self):
        return os.path.join(self.gnorm_root, "setup.txt")

    @property
    def gnorm_jar(self):
        return os.path.join(self.gnorm_root, "GNormPlus.jar")
