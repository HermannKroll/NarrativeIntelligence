import logging
import os
from shutil import copy
from argparse import ArgumentParser

from narraint.backend.models import Document
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS, ILLEGAL_CHAR


def sanitize(input_dir_or_file, output_dir=None, delete_mismatched=False, logger=logging):
    """
    Removes all "|" characters from pubtator files and cast out files lacking abstracts.
    :param input_dir_or_file: Input directory containing pubtator files or single pubtator file
    :param output_dir: Directory to output the sanitized files to. Default: operate on input_dir
    :param delete_mismatched: If set to true, files without abstract will be deleted from input_dir
    :return: (list of ignored files, list of sanitized files)
    """
    ignored_files = []
    sanitized_files = []
    if os.path.isdir(input_dir_or_file):
        raw_files = [os.path.join(input_dir_or_file, fn) for fn in os.listdir(input_dir_or_file)]
        if not output_dir:
            output_dir = input_dir_or_file
    else:
        raw_files = (input_dir_or_file,)
        if not output_dir:
            output_dir = os.path.dirname(input_dir_or_file)

    for file in raw_files:
        with open(file) as f:
            content = f.read()
            # content = content[0:len(content)-1] # trim \n added by read()
            reg_result = CONTENT_ID_TIT_ABS.match(content)
            if not reg_result:
                ignored_files.append(file)
                if delete_mismatched:
                    os.remove(file)
            else:
                pid, title, abstract = reg_result.groups()
                if abstract.strip() == "":
                    ignored_files.append(file)
                    if delete_mismatched:
                        os.remove(file)
                else:
                    new_filename = os.path.join(output_dir, os.path.basename(file))
                    if not ".txt" == new_filename[-4:]:
                        new_filename += ".txt"
                        sanitized_files.append(file)
                    if ILLEGAL_CHAR.search(title + abstract):
                        sanitized_files.append(file)
                        with open(new_filename, "w+") as nf:
                            nf.write(Document.create_pubtator(pid, title, abstract) + "\n")
                    else:
                        if not input_dir_or_file == output_dir:
                            copy(file, new_filename)
    return ignored_files, sanitized_files


def main():
    parser = ArgumentParser(description="Sanitize Pubtator documents removing illegal characters and removing "
                                        "misformatted")
    parser.add_argument("input", help="Directory with PubTator files or PubTator file", metavar="IN_DIR")
    parser.add_argument("-o", "--output", help="Output directory. Works on Input directory if not set.")
    parser.add_argument("-d", "--delete-misform", help="Delete misformatted files in input directory",
                        action='store_true')
    args = parser.parse_args()
    sanitize(args.input, args.output if args.output else None, args.delete_misform)


if __name__ == "__main__":
    main()
