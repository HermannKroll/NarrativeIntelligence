import time

import datetime
import httplib2
import re

import logging
from bs4 import BeautifulSoup

from narraint.progress import print_progress_with_eta
from narraint.tools import proj_rel_path


def build_url(letter, offset):
    return f"https://www.drugbase.de/en/databases/fiedler/excipients-a-z.html?tx_crondavdbfiedler_pi%5Babc%5D={letter}&tx_crondavdbfiedler_pi%5Boffset%5D={offset}&cHash=c4d3a47fcde6abca6ecb409dd2bc257d"

def main():

    extraction_list = []
    letters = [chr(n) for n in range(ord('A'), ord('Z')+1)] +['1','2']
    out_file = proj_rel_path("data/excipients.txt")

    with open(out_file, "w+") as f:
        pass

    for letter in letters:
        time.sleep(1)
        http = httplib2.Http()
        _,content = http.request(build_url(letter, 0))
        entries = int(re.search(r"(\d+)<\/strong> records found", content.decode()).group(1))
        for offset in range(0,entries, 20):
            logging.debug(f"At letter {letter} and Page {offset//20+1} of {entries//20+1}")
            time.sleep(1)
            if offset!=0:
                _, content = http.request(build_url(letter, offset))
            soup = BeautifulSoup(content, "html.parser")
            ul_search_results = soup.find(class_='search-results')
            extract = [li.a.contents[0] for li in ul_search_results.find_all('li')]
            #logging.debug(extract)
            extraction_list += [li.a.contents[0] for li in ul_search_results.find_all('li')]
        with open(out_file, "a+") as f:
            f.write("\n".join(extraction_list))
        extraction_list = []


if __name__ == '__main__':
    logging.basicConfig(level="DEBUG")
    main()