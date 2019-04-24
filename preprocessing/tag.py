import json
import os
import re
import subprocess
import tempfile
from argparse import ArgumentParser
from shutil import copyfile


class Config:
    def __init__(self, config_file):
        with open(config_file) as f:
            self.config = json.load(f)

    @property
    def tagger_one_root(self):
        return self.config["taggerOne"]["root"]

    @property
    def tagger_one_model(self):
        return os.path.join(self.tagger_one_root, self.config["taggerOne"]["model"])

    @property
    def tagger_one_script(self):
        return os.path.join(self.tagger_one_root, self.config["taggerOne"]["script"])

    @property
    def gnorm_root(self):
        return self.config["gnormPlus"]["root"]

    @property
    def gnorm_setup(self):
        return os.path.join(self.gnorm_root, self.config["gnormPlus"]["setup"])

    @property
    def gnorm_executable(self):
        return os.path.join(self.gnorm_root, self.config["gnormPlus"]["executable"])


title_pattern = re.compile(r"^\d+\|t\|")
abstract_pattern = re.compile(r"^\d+\|a\|")


def read_pubtator_file(filename):
    docs = {}
    with open(filename) as f:
        for line in f:
            if line.strip():
                did = re.findall(r"^\d+", line)[0]
                if did not in docs:
                    docs[did] = dict(title=None, abstract=None, tags=[])
                if title_pattern.match(line):
                    docs[did]["title"] = line.strip()
                elif abstract_pattern.match(line):
                    docs[did]["abstract"] = line.strip()
                else:
                    docs[did]["tags"] += [line.strip()]

    return docs


def merge_pubtator_files(file1, file2, output):
    d1 = read_pubtator_file(file1)
    d2 = read_pubtator_file(file2)

    ids = set(d1.keys()) | set(d2.keys())

    with open(output, "w") as f:
        for did in ids:
            if did in d1 and did not in d2:
                title = d1[did]["title"]
                abstract = d1[did]["abstract"]
                tags = d1[did]["tags"]
            elif did not in d1 and did in d2:
                title = d2[did]["title"]
                abstract = d2[did]["abstract"]
                tags = d2[did]["tags"]
            else:
                title = d1[did]["title"]
                abstract = d1[did]["abstract"]
                tags = d1[did]["tags"] + d2[did]["tags"]
            f.write(f"{title}\n")
            f.write(f"{abstract}\n")
            f.write("{}\n".format("\n".join(sorted(tags, key=lambda x: int(x.split("\t")[1])))))


# TODO: Add logging command
def tag_chemicals_diseases(config, input_file, output_file):
    print("Starting TaggerOne ...")
    subprocess.Popen([
        config.tagger_one_script,
        "Pubtator",
        config.tagger_one_model,
        input_file,
        output_file,
    ], cwd=config.tagger_one_root)


# TODO: Add logging command
def tag_genes(config, input_dir, output_dir):
    print("Starting GNormPlus ...")
    # script = os.path.join(GNORM, "GNormPlus.sh")
    sp_args = ["java", "-Xmx100G", "-Xms100G", "-jar", config.gnorm_executable, input_dir, output_dir,
               config.gnorm_setup]
    subprocess.Popen(sp_args, cwd=config.gnorm_root)


def main():
    parser = ArgumentParser(
        description="Tool uses TaggerOne and GNormPlus to tag an input file in the PubTator format")
    parser.add_argument("-g", "--genes", help="Tag genes")
    parser.add_argument("-t", "--cd", help="Tag chemicals and diseases")
    parser.add_argument("-o", "--out", help="Output file")
    parser.add_argument("--config", help="Config file", default="config.json")
    parser.add_argument("input", help="Input file in PubTator format")
    args = parser.parse_args()

    config = Config(args.config)

    input_filename = args.input.split("/")[-1]
    tmp_gnorm_input = tempfile.mkdtemp()
    tmp_gnorm_output = tempfile.mkdtemp()
    gnorm_output = os.path.join(tmp_gnorm_output, input_filename)
    tagger_one_output = os.path.join(tempfile.mkdtemp(), input_filename)

    if args.g:
        copyfile(args.i, os.path.join(tmp_gnorm_input, input_filename))
        tag_genes(config, tmp_gnorm_input, tmp_gnorm_output)
        print("Writing tagged genes to {}".format(gnorm_output))

    if args.t:
        tag_chemicals_diseases(config, args.i, tagger_one_output)
        print("Writing tagged chemicals/diseases to {}".format(tagger_one_output))

    if args.o and args.t and args.g:
        merge_pubtator_files(tagger_one_output, gnorm_output, args.o)


if __name__ == "__main__":
    main()
