"""
Module creates a single text file in the Pubtator format with the full text documents from list of PMCIDs and the
PubMedCentral Open Access Document collection.
"""
import os
import re
import sys
from argparse import ArgumentParser

from lxml import etree, html

# TODO: Merge into create_pubtator_format documentation (to visualize workflow)
# Sources
# Select descendants: https://stackoverflow.com/questions/6287646/xpath-how-to-select-all-children-and-grandchildren-regardless-of-depth-with
# Steps
# 1. Read nxml-files
# 2. Select relevant nodes:
#    - article.front.article-meta.title-group.abstract-title
#    - article.front.article-meta.abstract.p
#    - article.body.sec+.p
# 3. Delete HTML tags (completely remove table-wrap)
# 4. Write information to Pubtator format

table_wrap_pattern = re.compile(r"<table-wrap\s.*?</table-wrap>")


def clean_p_element(p_element):
    """
    Clean p-elements from a PubMedCentral nxml-file.

    Reason: p-elements contain tables which should not be included in the resulting file.

    :param p_element: XML-p-Element
    :return: Inner text from the p element without any tags or tables
    """
    xml_str = etree.tostring(p_element).decode("utf-8")
    xml_str = xml_str.strip().replace("\n", " ")
    xml_str = table_wrap_pattern.sub("", xml_str)
    text = html.fragment_fromstring(xml_str).text_content()
    text = text.strip().replace("\n", " ")
    return text


def create_pubtator_format(fn):
    """
    Method take a filename from an PMC-xml-file and returns the string in the PubTator format
    (e.g., <PMCID>|t| Title and <PMCID>|a| Content.

    .. note::

        The abstract and the body sections are merged into the "abstract" field of the PubTator file.

    :param str fn: Filename to the PMC-document in xml-format.
    :return: String for the PubTator representation
    """
    with open(fn) as f:
        tree = etree.parse(fn)

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

    pmcid = fn.split("/")[-1][3:-5]
    return "{pmcid}|t| {title}\n{pmcid}|a| {abst}\n".format(abst=pubtator_abstract, title=title, pmcid=pmcid)


# TODO: Add documentation
def collect_files(id_list_or_filename, search_directory):
    if isinstance(id_list_or_filename, str):
        with open(id_list_or_filename) as f:
            ids = set(line.strip() for line in f)
    else:
        ids = id_list_or_filename

    result_files = []
    for root, dirs, files in os.walk(search_directory):
        result_files.extend(os.path.join(root, fname) for fname in files if fname[:-5] in ids)

    return result_files


# TODO: Add documentation
def create_pubtator_file(pmc_files, output_filename):
    count = len(pmc_files)
    last_percent = 0
    with open(output_filename, "w") as f:
        for current, fn in enumerate(pmc_files):
            content = create_pubtator_format(fn)
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
    parser.add_argument("-o", help="Output file", default="documents.PubTator.txt")
    parser.add_argument("input", help="Input file with the PMCIDs. Each PMCID must be in an separate line.")
    parser.add_argument("dir", help="Top-level-directory which contains the PMC files. Subdirectory are searched, too.")
    args = parser.parse_args()

    pmc_files = collect_files(args.id_file, args.dir)
    create_pubtator_file(pmc_files, args.o)


if __name__ == "__main__":
    main()
