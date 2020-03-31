import tempfile
import os
import re
import sys
import traceback
import logging

from argparse import ArgumentParser
from typing import List
from lxml import etree, html
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.collect import PMCCollector
from narraint.preprocessing.config import Config
from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
from narraint.pubtator import conversion_errors

class PMCConverter:
    MAX_CONTENT_LENGTH = 500000
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

        # Long sentence fix
        xml_str = xml_str.replace("</p>", ".</p>")
        xml_str = xml_str.replace("<p>", "<p>.")

        for pattern in self.PATTERNS_TO_DELETE:
            xml_str = pattern.sub("", xml_str)
        text = html.fragment_fromstring(xml_str).text_content()
        text = self.clean_text(text)
        return text

    def convert(self, in_file, out_file, pmcid, pmid):
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
            If either abstract or title are missing an exception is thrown.

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
        :param str pmcid: PubMed Central Document ID
        :param str pmid: PubMed ID (PMCID ID will be replaced by PMID)
        :return: String for the PubTator representation
        """
        with open(in_file) as f:
            tree = etree.parse(f)

        # Select title
        e_title = tree.xpath("/article/front/article-meta/title-group/article-title")
        title = ''.join(e_title[0].itertext())
        if title:
            title = self.clean_text(title)

        # Select abstract (observation: abstract could have multiple paragraphs)
        e_abstract = tree.xpath("/article/front/article-meta/abstract//p")
        abstract = ''.join(self.clean_p_element(p) for p in e_abstract)

        # Select content (skip tables)
        e_content = tree.xpath("/article/body//p[parent::sec]")
        content = ".".join(self.clean_p_element(p) for p in e_content)

        # Merge abstract and content
        pubtator_abstract = "{} {}".format(abstract, content)
        pubtator_abstract = pubtator_abstract.strip()

        filename = in_file.split("/")[-1]
        pmcid_in_doc = filename[3:filename.rindex(".")]

        if pmcid_in_doc != pmcid:
            raise ValueError("PMCID in document does not match the expected PMCID...")

        # Finish
        if len(pubtator_abstract) > self.MAX_CONTENT_LENGTH:
            raise conversion_errors.DocumentTooLargeError

        if not title:
            raise conversion_errors.NoTitleError
        elif not pubtator_abstract:
            raise conversion_errors.NoAbstractError
        else:
            content = "{pmcid}|t| {title}\n{pmcid}|a| {abst}\n".format(abst=pubtator_abstract, title=title, pmcid=pmcid)
            content = content.replace(pmcid, pmid)
            # ensures that no \t are included
            content = content.replace('\t', ' ')
            with open(out_file, "w") as f:
                f.write("{}\n".format(content))

    def convert_bulk(self, filename_list: List[str], output_dir, pmcid2pmid, err_file=None):
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
            pmcid = ".".join(fn.split("/")[-1].split(".")[:-1]).replace('PMC', '')
            if pmcid in pmcid2pmid:
                pmid = pmcid2pmid[pmcid]
                try:
                    out_file = os.path.join(output_dir, f"{pmid}.txt")
                    self.convert(fn, out_file, pmcid, pmid)
                except conversion_errors.NoTitleError:
                    ignored_files.append(f"{fn}\nNo title was found!")
                except conversion_errors.NoAbstractError:
                    ignored_files.append(f"{fn}\nNo Abstract was found!")
                except conversion_errors.DocumentEmptyError:
                    ignored_files.append(f"{fn}\nDocument is empty!")
                except conversion_errors.DocumentTooLargeError:
                    ignored_files.append(f"{fn}\nDocument is too large!")
                except ValueError:
                    ignored_files.append(f"{fn}\n Mismatched ID: \n {traceback.format_exc()}")
                # TODO: Add more specific cases if encountered
                except:
                    ignored_files.append(f"{fn} \n Raised an exception: \n {traceback.format_exc()}")
            else:
                ignored_files.append('pmcid to pmid missing for {}'.format(fn))

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

def main():
    parser = ArgumentParser(description="Collect and convert PMC files from a list of pmc-ids")
    parser.add_argument("input", help="File containing PMC IDs OR directory containing PMC files")
    parser.add_argument("output", help="Directory to output the converted Files into")
    parser.add_argument("-c", "--collect", metavar="DIR", help="Collect PubMedCentral files from DIR")
    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=PREPROCESS_CONFIG,
                                help="Configuration file (default: {})".format(PREPROCESS_CONFIG))
    group_settings.add_argument("--loglevel", default="INFO")

    args = parser.parse_args()
    conf = Config(args.config)
    logging.basicConfig(level=args.loglevel.upper())

    collect_dir = args.collect if args.collect else conf.pmc_dir


    # TODO: Logfile
    if args.output:
        out_dir = args.output
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            logging.info(f"Creating output directory {out_dir}")
    else:
        out_dir = tempfile.mkdtemp()
        logging.info(f"No output given, created temp directory at {out_dir}")

    logging.info('Load PMCID to PMID translation file')
    pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)

    error_file = os.path.join(out_dir, "conversion_errors.txt")
    if os.path.isdir(args.input):
        files = [os.path.join(args.input, fn) for fn in os.listdir(args.input) if fn.endswith(".nxml")]
    else:
        collector = PMCCollector(collect_dir)
        files = collector.collect(args.input)
    translator = PMCConverter()
    translator.convert_bulk(files, out_dir, pmcid2pmid, error_file)


if __name__ == "__main__":
    main()
