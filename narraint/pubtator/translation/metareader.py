import csv


class MetaReader:
    def __init__(self, metadata_file):
        self.path = metadata_file
        self._metadata_list = self._read_metadata()
        self._docid_dict = self._create_docid_index()
        self.cord_uid_index = self._create_cord_uid_index()

    def get_metadata_by_id(self, doc_id):
        return self._metadata_list[self._docid_dict[doc_id]]

    def __len__(self):
        return len(self._metadata_list)

    def _create_cord_uid_index(self):
        return {row['cord_uid']: index for index, row in enumerate(self._metadata_list)}

    def _create_docid_index(self):
        docid_dict = {}
        for index, row in enumerate(self._metadata_list):
            for sha in row['sha']:
                docid_dict[sha]=index
            for pmcid in row['pmcid']:
                docid_dict[pmcid] = index
        return docid_dict

    def _read_metadata(self):
        with open(self.path, 'r') as f:
            reader = csv.DictReader(f)
            dict_list = []
            for d in reader:
                for k in d.keys():
                    d[k] = d[k].split(";") # Iterpret ';'-splitted values as list
                dict_list.append(d)
            return dict_list
