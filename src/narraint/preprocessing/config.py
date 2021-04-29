import json
import os


class Config:
    """
    Wrapper class for JSON config file. Wraps base configuration and tagger configuration.
    """

    def __init__(self, config_file):
        with open(config_file) as f:
            self.config = json.load(f)

    @property
    def pmc_dir(self):
        return self.config["pmc_dir"]

    @property
    def pmcid2pmid(self):
        return self.config["pmcid2pmid"]

    # TaggerOne
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
    def tagger_one_timeout(self):
        return self.config["taggerOne"]["timeout"]

    @property
    def tagger_one_max_retries(self):
        return self.config["taggerOne"]["max_retries"]

    # GNormPlus
    @property
    def gnorm_root(self):
        return self.config["gnormPlus"]["root"]

    @property
    def gnorm_java_args(self):
        return self.config["gnormPlus"]["javaArgs"].split()

    @property
    def gnorm_setup(self):
        return os.path.join(self.gnorm_root, "setup.txt")

    @property
    def gnorm_jar(self):
        return os.path.join(self.gnorm_root, "GNormPlus.jar")

    # DNorm
    @property
    def dnorm_root(self):
        return self.config["dnorm"]

    @property
    def dnorm_script(self):
        return os.path.join(self.dnorm_root, "RunDNorm.sh")

    @property
    def dnorm_config(self):
        return os.path.join(self.dnorm_root, "config/banner_NCBIDisease_TEST.xml")

    @property
    def dnorm_lexicon(self):
        return os.path.join(self.dnorm_root, "data/CTD_diseases.tsv")

    @property
    def dnorm_matrix(self):
        return os.path.join(self.dnorm_root, "output/simmatrix_NCBIDisease_e4.bin")

    # tmChem
    @property
    def tmchem_root(self):
        return self.config["tmchem"]

    @property
    def tmchem_script(self):
        return os.path.join(self.tmchem_root, "run.sh")

    @property
    def dict_max_words(self):
        return self.config["dict"]["max_words"]

    @property
    def dict_check_abbreviation(self):
        return self.config["dict"]["check_abbreviation"]

    #@property
    #def dict_resolve_conjunctions(self):
    #    return self.config["dict"]["resolve_conjunctions"].lower=="true"

    @property
    def custom_abbreviations(self):
        return self.config["dict"]["custom_abbreviations"]

    @property
    def dict_min_full_tag_len(self):
        return self.config["dict"]["min_full_tag_len"]

    @property
    def drug_check_products(self):
        return self.config["drug"]["check_products"]

    @property
    def drug_max_per_product(self):
        return self.config["drug"]["max_per_product"]

    @property
    def drug_min_name_length(self):
        return self.config["drug"]["min_name_length"]

    @property
    def ignore_excipient_terms(self):
        return self.config["drug"]["ignore_excipient_terms"]