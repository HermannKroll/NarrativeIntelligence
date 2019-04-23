"""
Module creates a single text file in the Pubtator format with the full text documents from list of PMCIDs and the
PubMedCentral Open Access Document collection.

*Which PubMedCentral files are collected?*

The module collects all PubMedCentral files with a user-specified ID.

This set of documents is scanned for text, contained in a p-Node, which is child of a sec-Node.
Some documents do not follow this schema (e.g., PMC3153655, which is a schedule for the SNIP conference).

"""
import os
import re
import sys
from argparse import ArgumentParser

from lxml import etree, html

patterns_to_delete = (
    re.compile(r"<table-wrap\s.*?</table-wrap>"),  # <table-wrap>
    re.compile(r"<inline-formula\s.*?</inline-formula>"),  # <inline-formula>
    re.compile(r"<disp-formula\s.*?</disp-formula>"),  # <discpp-formula>
    re.compile(r"<tex-math\s.*?</tex-math>"),  # <tex-math>
    re.compile(r"<xref\s.*?</xref>"),  # <xref>
    re.compile(r"<fig\s.*?</fig>"),  # <fig>
)


def clean_p_element(p_element):
    """
    Clean p-elements from a PubMedCentral nxml-file.

    Reason: p-elements contain tables and other undesired information which should not be included in the resulting file.

    :param p_element: XML-p-Element
    :return: Inner text from the p element without any undesired tags
    """
    xml_str = etree.tostring(p_element).decode("utf-8")
    xml_str = xml_str.strip().replace("\n", " ")
    for pattern in patterns_to_delete:
        xml_str = pattern.sub("", xml_str)
    text = html.fragment_fromstring(xml_str).text_content()
    text = text.strip().replace("\n", " ")
    return text


def create_pubtator_format(fn):
    """
    Method takes a filename from an PMC-xml-file and returns the string in the PubTator format
    (e.g., <PMCID>|t| <Title> and <PMCID>|a| <Content>).
    The complete content of the file is placed into the section of the abstract.
    The following tags are ignored:

    - xref
    - table-wrap
    - inline-formula
    - disp-formula
    - fig
    - tex-math

    .. note::

        The abstract and the body sections are merged into the "abstract" field of the PubTator file.
        If no abstract is found, only the title is returned.

    .. seealso::

        https://stackoverflow.com/questions/6287646/xpath-how-to-select-all-children-and-grandchildren-regardless-of-depth-with

    *Workflow*

    1. Read nxml-files
    2. Select relevant nodes:
        - article.front.article-meta.title-group.abstract-title
        - article.front.article-meta.abstract.p
        - article.body.sec+.p
    3. Delete HTML tags (remove tags like xref, tex-math, table-wrap, etc.)
    4. Write information to Pubtator format

    :param str fn: Filename to the PMC-document in xml-format.
    :return: String for the PubTator representation
    """
    with open(fn) as f:
        tree = etree.parse(f)

    # Select title
    e_title = tree.xpath("/article/front/article-meta/title-group/article-title")
    title = e_title[0].text

    # Select abstract (observation: abstract could have multiple paragraphs)
    e_abstract = tree.xpath("/article/front/article-meta/abstract//p")
    abstract = " ".join(clean_p_element(p) for p in e_abstract)

    # Select content (skip tables)
    e_content = tree.xpath("/article/body//p[parent::sec]")
    content = " ".join(clean_p_element(p) for p in e_content)

    # Merge abstract and content
    pubtator_abstract = "{} {}".format(abstract, content)

    filename = fn.split("/")[-1]
    pmcid = filename[3:filename.rindex(".")]

    if pubtator_abstract.strip() and title:
        return "{pmcid}|t| {title}\n{pmcid}|a| {abst}\n".format(abst=pubtator_abstract, title=title, pmcid=pmcid)
    else:
        return ""

def collect_files(id_list_or_filename, search_directory):
    """
    Method searches ``search_directory`` recursively for files starting with a specific id.
    Method either takes a filename or a list. The file should contain the ids (one id per line).
    Method returns a list of absolute paths to the files starting with the specific id.

    :param id_list_or_filename: List of ids / filename to a file containing the ids
    :param search_directory: Directory to search for
    :return: List of absolute paths to found files
    """
    sys.stdout.write("Collecting files ...")
    sys.stdout.flush()
    if isinstance(id_list_or_filename, str):
        with open(id_list_or_filename) as f:
            ids = set(line.strip() for line in f)
    else:
        ids = id_list_or_filename

    result_files = []
    for root, dirs, files in os.walk(search_directory):
        result_files.extend(os.path.join(root, fname) for fname in files if fname[:-5] in ids)

    sys.stdout.write(" done.\n")
    sys.stdout.flush()

    return result_files


def create_pubtator_file(pmc_files, output_filename):
    """
    Method creates one PubTator file from a list on PMC input files.

    :param pmc_files: List of absolute paths to PMC files
    :param output_filename: PubTator file
    """
    count = len(pmc_files)
    last_percent = 0
    with open(output_filename, "w") as f:
        for current, fn in enumerate(pmc_files):
            content = create_pubtator_format(fn)
            if content:
                f.write("{}\n".format(content))

            # Output
            if ((current + 1) / count * 100.0) > last_percent:
                last_percent = int((current + 1) / count * 100.0)
                sys.stdout.write("\rMerging ... {} %".format(last_percent))
                sys.stdout.flush()
    sys.stdout.write("\nDone.\n")


# TODO: Add documentation
def main():
    parser = ArgumentParser(
        description="Tool collects all PMC documents with a specific PMCID and unions them into a single PubTator file.")
    group = parser.add_argument_group('Collection group')
    group.add_argument("-o", help="Output file", default="documents.PubTator.txt", metavar="FILE")
    group.add_argument("--input", help="Input file with the PMCIDs. Each PMCID must be in an separate line.",
                       metavar="FILE")
    group.add_argument("--dir",
                       help="Top-level-directory which contains the PMC files. Subdirectory are searched, too.",
                       metavar="DIRECTORY")
    # More powerful/debug args
    parser.add_argument("--create-pubtator-format", metavar="FILE",
                        help="Create PubTator format from PMC file. Debug only.")
    args = parser.parse_args()

    if args.create_pubtator_format:
        print(create_pubtator_format(args.create_pubtator_format))
        sys.exit(0)

    pmc_files = collect_files(args.input, args.dir)
    create_pubtator_file(pmc_files, args.o)


if __name__ == "__main__":
    main()
