import argparse
import os
import pickle
from datetime import datetime

from lxml import etree

from narraint.config import MEDLINE_BASELINE_INDEX
from narraint.progress import print_progress_with_eta


class PubMedMEDLINE:
    def __init__(self):
        if not os.path.exists(MEDLINE_BASELINE_INDEX):
            raise ValueError("Index file {} can not be found.".format(MEDLINE_BASELINE_INDEX))
        with open(MEDLINE_BASELINE_INDEX, "rb") as f:
            self.desc_to_pmids = pickle.load(f)

    def get_ids(self, desc):
        if desc in self.desc_to_pmids:
            return self.desc_to_pmids[desc]
        else:
            return set()


def load_file(filename):
    with open(filename) as f:
        tree = etree.parse(f)

    pmid_to_descs = {}
    for article in tree.iterfind("PubmedArticle"):
        descs = set()
        # Get PMID
        pmids = article.findall("./MedlineCitation/PMID")
        if len(pmids) > 1:
            print("WARNING {}: More than one PMID found".format(filename))
            continue  # BAD
        else:
            pmid = int(pmids[0].text)

        # Parse Mesh heading
        for mh in article.iterfind("./MedlineCitation/MeshHeadingList/MeshHeading"):
            descriptors = mh.findall("./DescriptorName")
            if len(descriptors) > 1:
                print("WARNING {}: Doc {} contains more than one descriptor per Mesh heading".format(filename, pmid))
                continue  # BAD
            else:
                base_desc = descriptors[0].get("UI")
                descs.add(base_desc)

            for qualifier in mh.iterfind("./QualifierName"):
                desc = "{}_{}".format(base_desc, qualifier.get("UI"))
                descs.add(desc)

        # Parse Chemical list
        for c in article.iterfind("./MedlineCitation/ChemicalList/Chemical/NameOfSubstance"):
            desc = c.get("UI")
            descs.add(desc)

        pmid_to_descs[pmid] = descs

    return pmid_to_descs


def load_files(directory):
    desc_to_pmids = {}

    files = [os.path.join(directory, fn) for fn in os.listdir(directory) if fn.endswith(".xml")]

    start = datetime.now()
    for idx, fn in enumerate(files):
        pmid_to_descs = load_file(fn)
        for pmid, descs in pmid_to_descs.items():
            for desc in descs:
                if desc not in desc_to_pmids:
                    desc_to_pmids[desc] = {pmid}
                else:
                    desc_to_pmids[desc].add(pmid)

        print_progress_with_eta("Processing XML files", idx, len(files), start, 1)

    return desc_to_pmids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-index", "-i", help="Build index", action="store_true")
    parser.add_argument("directory", help="Directory containing XML files", metavar="DIR")
    args = parser.parse_args()

    if args.build_index:
        desc_to_pmids = load_files(args.directory)

        print("\nPickling index ...")
        with open(MEDLINE_BASELINE_INDEX, "wb")as f:
            pickle.dump(desc_to_pmids, f)
    else:
        print("Nothing to do")


if __name__ == "__main__":
    main()
