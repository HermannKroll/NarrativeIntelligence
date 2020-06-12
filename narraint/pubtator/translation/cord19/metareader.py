import csv

from narraint.pubtator.translation.md5_hasher import get_md5_hash_str

class MetaReader:
    """
    reads a metadata.csv file of a cord19 dump. Fields vor version 29:
        cord_uid,sha,source_x,title,doi,pmcid,pubmed_id,license,abstract,publish_time,
        authors,journal,mag_id,who_covidence_id,arxiv_id,pdf_json_files,pmc_json_files,url,s2_id
    """
    def __init__(self, metadata_file):
        self.path = metadata_file
        self.metadata_list = self._read_metadata()
        self._docid_dict = self._create_docid_index()
        self.cord_uid_index = self._create_cord_uid_index()

    def get_metadata_by_id(self, doc_id):
        return self.metadata_list[self._docid_dict[doc_id]]

    def get_metadata_by_cord_uid(self, cord_uid):
        return self.metadata_list[self.cord_uid_index[cord_uid]]

    def __len__(self):
        return len(self.metadata_list)

    def _create_cord_uid_index(self):
        return {"".join(row['cord_uid']): index for index, row in enumerate(self.metadata_list)}

    def _create_docid_index(self):
        docid_dict = {}
        for index, row in enumerate(self.metadata_list):
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
                    d[k] = [s.strip() for s in d[k].split(";")] # Iterpret ';'-splitted values as list
                dict_list.append(d)
            return dict_list

    def get_doc_content(self, cord_uid, generate_md5=False):
        """
        Get title, abstract and optional md5 of document from metadata
        :param cord_uid: corduid of docuemnt to get
        :param generate_md5: Set to true if md5 should be generated
        :return: (title, abstract,md5) if generate_md5 else (title, abstract)
        """
        metadata = self.get_metadata_by_cord_uid(cord_uid)
        title = ";".join(metadata['title'])
        abstract = ";".join(metadata['abstract'])
        return title, abstract, get_md5_hash_str(title+abstract) if generate_md5 else None