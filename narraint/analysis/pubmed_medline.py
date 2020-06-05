import argparse
import os
import pickle
from collections import defaultdict
from datetime import datetime

from lxml import etree

from narraint.backend.database import Session
from narraint.backend.models import DocProcessedByOpenIE
from narraint.config import MEDLINE_BASELINE_INDEX
from narraint.progress import print_progress_with_eta


class PubMedMEDLINE:
    """
    Query interface for the PubMed sample. Requires pickled dictionary (descriptor -> set of pmids).
    """

    def __init__(self):
        if not os.path.exists(MEDLINE_BASELINE_INDEX):
            raise ValueError("Index file {} can not be found.".format(MEDLINE_BASELINE_INDEX))
        with open(MEDLINE_BASELINE_INDEX, "rb") as f:
            self.desc_to_pmids = pickle.load(f)

        self.pmid_to_descs = None

    def create_reverse_index(self):
        """
        computes an reverse index which maps a document to it's set of mesh descriptors
        :return: None
        """
        self.pmid_to_descs = defaultdict(list)
        for k, pmids in self.desc_to_pmids.items():
            for pmid in pmids:
                self.pmid_to_descs[pmid].append(k)

    def _get_ids(self, desc):
        """
        Helper function for a single descriptor.
        :param str desc: Descriptor
        :return: set of pmids
        """
        if desc in self.desc_to_pmids:
            return self.desc_to_pmids[desc]
        else:
            return set()

    def get_ids(self, *descs):
        """
        Query a list of descriptors and return a set of pmids all containing these descriptors.
        Input *descs* may be a single list or a split list.

        :param descs: List of descriptors
        :return: Set of PMIDs all containing the descriptors
        """
        desc_list = []
        pmids = set()
        if descs:
            if isinstance(descs[0], list):
                desc_list = descs[0]
            else:
                desc_list = list(descs)
        for idx, desc in enumerate(desc_list):
            if ' ' in desc:
                raise ValueError('does not expect a empty space in : {}'.format(desc))
            if idx == 0:
                pmids = self._get_ids(desc)
            else:
                pmids = pmids.intersection(self._get_ids(desc))

        return pmids


def load_file(filename, db_pmids=None):
    """
    Process the XML file *filename* and only process the documents whose PMID is contained in *dm_pmids*.
    One file contains multiple documents.

    .. note::

       Some descriptors are artificial. Descriptors and Qualifiers are concatenated by an "_", e.g., D001 and Q001
       become D001_Q001.

    :param filename: Filename of XML file
    :param db_pmids: Set of PMIDs (int) to process
    :return: Dictionary PMID -> set(Descriptors)
    """
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

        if db_pmids:
            if pmid not in db_pmids:
                continue  # BAD

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


def load_files(directory, db_pmids=None):
    """
    Process a directory containg XML files. Only process those whose PMID is in *db_pmids*.
    Return a mapping from Descriptor to PMID

    :param directory:
    :param db_pmids:
    :return:
    """
    desc_to_pmids = {}

    files = [os.path.join(directory, fn) for fn in os.listdir(directory) if fn.endswith(".xml")]

    start = datetime.now()
    for idx, fn in enumerate(files):
        pmid_to_descs = load_file(fn, db_pmids)
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
    parser.add_argument("--build-index", "-i", help="Build index (default: {})".format(MEDLINE_BASELINE_INDEX),
                        const=MEDLINE_BASELINE_INDEX, metavar="INDEX_FILE", nargs="?")
    parser.add_argument("--dir", "-d", help="Directory containing XML files", metavar="DIR", required=True)
    parser.add_argument("--query", "-q", help="Query PMIDs", metavar="DESC", nargs="+")
    args = parser.parse_args()

    # Query database
    session = Session.get()
    query = session.query(DocProcessedByOpenIE.document_id).filter(DocProcessedByOpenIE.document_collection == "PMC")
    results = session.execute(query)
    db_pmids = set(x[0] for x in results)
    print("DB: {} documents processed by OpenID".format(len(db_pmids)))

    # Build index
    if args.build_index:
        desc_to_pmids = load_files(args.dir, db_pmids)

        print("\nPickling index ...")
        with open(args.build_index, "wb")as f:
            pickle.dump(desc_to_pmids, f)
    elif args.query:
        qi = PubMedMEDLINE()
        pmids = qi.get_ids(args.query)
        print("PMIDs:")
        print("\n".join(str(x) for x in pmids))
    else:
        print("Nothing to do")


if __name__ == "__main__":
    main()
