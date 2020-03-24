from xml.etree.ElementTree import iterparse


class MeSHDBSupplementary:
    """
    Class is a Singleton for the MeSH Supplementary database.
    You can load a descriptor file and query descriptors with the functions

    - desc_by_id
    - desc_by_tree_number
    - descs_by_name
    - descs_by_term

    Use the instance() method to get a MeSHDB instance.
    """
    __instance = None

    @staticmethod
    def instance():
        if MeSHDBSupplementary.__instance is None:
            MeSHDBSupplementary()
        return MeSHDBSupplementary.__instance

    def __init__(self):
        self._desc_by_id = dict()
        self._desc_by_name = dict()
        if MeSHDBSupplementary.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MeSHDBSupplementary.__instance = self

    def _parse_xml_incrementally(self, filename):
        doc = iterparse(filename, ('start', 'end'))
        # skip the root element
        next(doc)
        tag_stack, elem_stack = [], []
        started = False
        desc_ui, desc_heading = None, None
        for event, elem in doc:
            if event == 'start' and elem.tag == "SupplementalRecord":
                started = True
            if started:
                # extract the id
                if elem.tag == "SupplementalRecordUI":
                    desc_ui = elem.text
                # last element on stack was record name string
                if event == 'end' and elem.tag == "SupplementalRecordName":
                    desc_heading = elem_stack[-1].text
                tag_stack.append(elem.tag)
                elem_stack.append(elem)
            if event == 'end' and elem.tag == "SupplementalRecord":
                started = False
                yield desc_ui, desc_heading
                elem_stack.clear()
                tag_stack.clear()
                desc_ui, desc_heading = None, None

    def get_all_descs(self, filename):
        descs = []
        for idx, record in enumerate(self._parse_xml_incrementally(filename)):
            unique_id, heading = record
            desc = SupplementaryDescriptor(unique_id, heading)
            descs.append(desc)
        return descs

    def add_desc(self, desc_obj):
        """
        Adds an descriptor to the indexes.

        .. note::

           The try-except was introduced because some descriptors (e.g., Female) don't have a tre number.

        :param desc_obj: Descriptor object to add
        """
        self._desc_by_id[desc_obj.unique_id] = desc_obj
        self._desc_by_name[desc_obj.heading] = desc_obj


class SupplementaryDescriptor:

    def __init__(self, unique_id, heading):
        self.unique_id = unique_id
        self.heading = heading

