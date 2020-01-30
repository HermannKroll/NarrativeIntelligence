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
from typing import List

from lxml import etree, html
from lxml.etree import ParserError

from narraint.preprocessing.collect import PMCCollector

MAX_CONTENT_LENGTH = 500000
FMT_EPA_TTL = "TIB-EPA"
FMT_PMC_XML = "PMC-XML"
FMT_CHOICES = (
    FMT_EPA_TTL,
    FMT_PMC_XML,
)


class DocumentTooLargeError(Exception):
    pass


class DocumentEmptyError(Exception):
    pass


class PMCConverter:
    PATTERNS_TO_DELETE = (
        re.compile(r"<table-wrap\s.*?</table-wrap>"),  # <table-wrap>
        re.compile(r"<inline-formula\s.*?</inline-formula>"),  # <inline-formula>
        re.compile(r"<disp-formula\s.*?</disp-formula>"),  # <discpp-formula>
        re.compile(r"<tex-math\s.*?</tex-math>"),  # <tex-math>
        re.compile(r"<xref\s.*?</xref>"),  # <xref>
        re.compile(r"<fig\s.*?</fig>"),  # <fig>
    )

    @staticmethod
    def clean_text(text):
        cleaned = text.replace("|", "")
        cleaned = cleaned.replace("\n", " ")
        cleaned = cleaned.replace("\u2028", " ")
        cleaned = cleaned.strip()
        return cleaned

    def clean_p_element(self, p_element):
        """
        Clean p-elements from a PubMedCentral nxml-file.

        Reason: p-elements contain tables and other undesired information which should not be included in the resulting file.

        :param p_element: XML-p-Element
        :return: Inner text from the p element without any undesired tags
        """
        xml_str = etree.tostring(p_element).decode("utf-8")
        xml_str = xml_str.strip().replace("\n", " ")
        for pattern in self.PATTERNS_TO_DELETE:
            xml_str = pattern.sub("", xml_str)
        text = html.fragment_fromstring(xml_str).text_content()
        text = self.clean_text(text)
        return text

    def convert(self, in_file, out_file):
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

        :param str out_file: Output
        :param str in_file: Filename to the PMC-document in xml-format.
        :return: String for the PubTator representation
        """
        with open(in_file) as f:
            tree = etree.parse(f)

        # Select title
        e_title = tree.xpath("/article/front/article-meta/title-group/article-title")
        title = e_title[0].text
        if title:
            title = self.clean_text(title)

        # Select abstract (observation: abstract could have multiple paragraphs)
        e_abstract = tree.xpath("/article/front/article-meta/abstract//p")
        abstract = " ".join(self.clean_p_element(p) for p in e_abstract)

        # Select content (skip tables)
        e_content = tree.xpath("/article/body//p[parent::sec]")
        content = " ".join(self.clean_p_element(p) for p in e_content)

        # Merge abstract and content
        pubtator_abstract = "{} {}".format(abstract, content)
        pubtator_abstract = pubtator_abstract.strip()

        filename = in_file.split("/")[-1]
        pmcid = filename[3:filename.rindex(".")]

        # Finish
        if len(pubtator_abstract) > MAX_CONTENT_LENGTH:
            raise DocumentTooLargeError

        if pubtator_abstract.strip() and title:
            content = "{pmcid}|t| {title}\n{pmcid}|a| {abst}\n".format(abst=pubtator_abstract, title=title, pmcid=pmcid)
            with open(out_file, "w") as f:
                f.write("{}\n".format(content))
        else:
            raise DocumentEmptyError

    def convert_bulk(self, filename_list: List[str], output_dir, err_file=None):
        """
        Method converts a set of PubMedCentral XML files to the PubTator format.

        :param err_file:
        :param filename_list: List of absolute paths to PMC files
        :param output_dir: Directory
        """
        count = len(filename_list)
        ignored_files = []
        last_percent = 0

        for current, fn in enumerate(filename_list):
            pmcid = ".".join(fn.split("/")[-1].split(".")[:-1])
            try:
                out_file = os.path.join(output_dir, f"{pmcid}.txt")
                try:
                    self.convert(fn, out_file)
                except (DocumentEmptyError, DocumentTooLargeError):
                    pass
                else:
                    ignored_files.append(fn)
            except:
                ignored_files.append(fn)

            # Output
            if ((current + 1) / count * 100.0) > last_percent:
                last_percent = int((current + 1) / count * 100.0)
                sys.stdout.write("\rConverting ... {} %".format(last_percent))
                sys.stdout.flush()

        sys.stdout.write(" done ({} files processed, {} errors)\n".format(count, len(ignored_files)))

        if err_file:
            with open(err_file, "w") as f:
                f.write("\n".join(ignored_files))
            print("See {} for a list of ignored files.".format(err_file))


class PatentConverter:
    """
    Convert TIB patents dump to collection of PubTator documents.

    .. note:

       Patents are identified using a country code and an ID, which are only unique in combination. Since PubTator
       IDs need to be digits, we replace the country code with a unique digit.
    """
    REGEX_ID = re.compile(r"^\d+$")
    COUNTRIES = {"AU", "CN", "WO", "GB", "US", "EP", "CA"}
    COUNTY_PREFIX = dict(
        AU=1,
        CN=2,
        WO=3,
        GB=4,
        US=5,
        EP=6,
        CA=7,
    )

    def convert(self, in_file, out_dir):
        """
        `in_file` is the file preprocessed by the Academic library of the TU Braunschweig.

        :param in_file: File for the TIB dump
        :param out_dir: Directory with PubTator files for TIB
        :return:
        """
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        print("Reading file ...")
        title_by_id = dict()
        abstract_by_id = dict()
        count = 0
        with open(in_file) as f:
            for idx, line in enumerate(f):
                id_part, body = line.strip().split("|", maxsplit=1)
                did = id_part[id_part.rindex(":") + 1:]
                country_code = did[:2]
                patent_id = did[2:]
                if country_code in self.COUNTRIES and self.REGEX_ID.fullmatch(patent_id):
                    count += 1
                    did = "{}{}".format(self.COUNTY_PREFIX[country_code], patent_id)
                    if idx % 2 == 0:
                        title_by_id[did] = body.title()
                    else:
                        abstract_by_id[did] = body

        sys.stdout.write("Writing {}/{} patents ...".format(int(count / 2), int((idx + 1) / 2)))
        total = len(title_by_id.keys())
        count = 0
        last_percentage = 0
        for did, title in title_by_id.items():
            if did in abstract_by_id:
                out_fn = os.path.join(out_dir, "{}.txt".format(did))
                with open(out_fn, "w") as f:
                    f.write("{}|t|{}\n".format(did, title))
                    f.write("{}|a|{}\n\n".format(did, abstract_by_id[did]))
            else:
                print("WARNING: Document {} has no abstract".format(did))
            current_percentage = int((count + 1.0) / total * 100.0)
            if current_percentage > last_percentage:
                sys.stdout.write("\rWriting {}/{} patents ... {} %".format(count + 1, total,
                                                                           current_percentage))
                last_percentage = current_percentage
            count += 1
        print(" done")


def main():
    parser = ArgumentParser(description="Tool to convert PubMedCentral XML files/Patent files to Pubtator format")

    parser.add_argument("-c", "--collect", metavar="DIR", help="Collect PubMedCentral files from DIR")
    parser.add_argument("-f", "--format", help="Format of input files", default=FMT_PMC_XML,
                        choices=FMT_CHOICES)

    parser.add_argument("input", help="Input file/directory", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    if args.format == FMT_PMC_XML:
        t = PMCConverter()
        if args.collect:
            collector = PMCCollector(args.collect)
            files = collector.collect(args.input)
            t.convert_bulk(files, args.output)
        else:
            if os.path.isdir(args.input):
                files = [os.path.join(args.input, fn) for fn in os.listdir(args.input) if fn.endswith(".nxml")]
                t.convert_bulk(files, args.output)
            else:
                t.convert(args.input, args.output)

    if args.format == FMT_EPA_TTL:
        if args.collect:
            print("WARNING: Ignoring --collect")
        t = PatentConverter()
        t.convert(args.input, args.output)


if __name__ == "__main__":
    main()
