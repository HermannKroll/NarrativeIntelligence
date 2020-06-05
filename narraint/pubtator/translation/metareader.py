import csv


class MetaReader:
    def __init__(self, metadata_file):
        self.path = metadata_file
        self._metadata_list = _read_metadata(metadata_file)
        self._docid_dict = _create_docid_index(self._metadata_list)

    def get_metadata_by_id(self, doc_id):
        return self._metadata_list[self._docid_dict[doc_id]]

    def __len__(self):
        return len(self._metadata_list)


def _create_docid_index(metadata_list):
    docid_dict={}
    for index, row in enumerate(metadata_list):
        for sha in row['sha']:
            docid_dict[sha]=index
        for pmcid in row['pmcid']:
            docid_dict[pmcid]=index
    return docid_dict


def _read_metadata(metadata_file):
    with open(metadata_file, 'r') as f:
        reader = csv.DictReader(f)
        dict_list = []
        for d in reader:
            for k in d.keys():
                d[k] = d[k].split(";") # Iterpret ';'-splitted values as list
            dict_list.append(d)
        return dict_list
