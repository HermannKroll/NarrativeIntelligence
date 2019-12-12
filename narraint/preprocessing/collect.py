import os
import sys


class PMCCollector:
    def __init__(self, search_directory):
        self.search_directory = search_directory

    def get_ids(self, id_list_or_filename):
        if isinstance(id_list_or_filename, str):
            with open(id_list_or_filename) as f:
                ids = set(line.strip() for line in f)
        else:
            ids = set(id_list_or_filename)
        return ids

    def collect(self, id_list_or_filename):
        """
        Method searches ``search_directory`` recursively for files starting with a specific id.
        Method either takes a filename or a list. The file should contain the ids (one id per line).
        Method returns a list of absolute paths to the files starting with the specific id.

        :param id_list_or_filename: List of ids / filename to a file containing the ids
        :return: List of absolute paths to found files
        """
        sys.stdout.write("Collecting files ...")
        sys.stdout.flush()
        ids = self.get_ids(id_list_or_filename)

        result_files = []
        for root, dirs, files in os.walk(self.search_directory):
            result_files.extend(os.path.join(root, fname) for fname in files if fname[:-5] in ids)

        sys.stdout.write(" done.\n")
        sys.stdout.flush()

        return result_files
