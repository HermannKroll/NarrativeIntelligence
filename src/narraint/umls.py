"""
Create mapping from UMLS concept ID to MESH ID

Use dataset: 2019AA UMLS Metathesaurus Files
- [MRCONSO.RRF](https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html)
- [Information](https://www.ncbi.nlm.nih.gov/books/NBK9685/#ch03.sec3.3.4)
"""
import gzip
import json
from datetime import datetime

from narraint.config import UMLS_DATA, UMLS_MAPPING


def main():
    mapping = dict()

    start = datetime.now()
    with gzip.open(UMLS_DATA) as f:
        for idx, line in enumerate(f):
            fields = line.split("|")
            if fields[11] == "MSH":
                if fields[0] not in mapping:
                    mapping[fields[0]] = fields[10]
    end = datetime.now()

    print("Read {} lines in {}".format(idx + 1, end - start))
    with open(UMLS_MAPPING, "w") as f:
        json.dump(mapping, f)


if __name__ == "__main__":
    main()
