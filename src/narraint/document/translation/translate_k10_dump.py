import json
import time
from os import path, scandir
from typing import List, Optional, IO, Dict, AnyStr
from json import load, loads, dumps

JSON_RESPONSE_KEY = "response"
JSON_RESPONSE_DOCS_KEY = "docs"

PATH = "../../../kroll/k10Plus_Dump_2022-02-28"
JSON_READS = 1000


def loading_format_from_file(file_path: AnyStr) -> List:
    """
    Returns a dict of lists containing articles sorted by the collection.
    Can be potentially empty.

    :param file_path: AnyStr
    :return: Dict[AnyStr: List]
    """
    _data = open(file_path)  # TODO: catch invalid file path error?
    _articles = get_document_list(_data)
    article_list: List = list()

    for _article in _articles:
        # print(doc) # DEBUG

        # map invalid keys (as params) into valid ones
        if "author-letter" in _article.keys():
            _article["author_letter"] = _article["author-letter"]
            _article.pop("author-letter", "Key not found")
        if "id" in _article.keys():
            _article["article_id"] = _article["id"]
            _article.pop("id", "Key not found")
        if "publishDate" in _article.keys():
            _article["publish_date"] = _article["publishDate"]
            _article.pop("publishDate")

        new_articles = generate_loading_format(**_article)
        if new_articles:
            article_list.extend(new_articles)

    return article_list


def get_document_list(file_stream: IO) -> List[Dict]:
    """
    Return a list (X) of articles contained in the following structure
    "response": { "docs":[X] }

    :param file_stream: IO
    :return: List[Dict]
    """
    return loads(dumps(loads(dumps(
        load(file_stream)[JSON_RESPONSE_KEY]))[JSON_RESPONSE_DOCS_KEY]))


def get_json_files(directory: AnyStr) -> Optional[List[AnyStr]]:
    """
    Return a list of '.json' files contained in the 'directory', None in
    case of an invalid directory parameter.

    :param directory: AnyStr
    :return: Optional[List[str]]
    """
    if not path.exists(directory) or not path.isdir(directory):
        # return 'None' if the given 'directory' is invalid
        return None

    dir_entries = scandir(directory)
    file_list: List[AnyStr] = list()

    for entry in dir_entries:
        entry_name = path.join(directory, entry.name)
        if not path.isfile(entry_name):
            continue

        if entry_name.endswith(".json"):
            file_list.append(entry_name)

    return file_list


def generate_loading_format(article_id=None, collection=None, abstract=None,
                            title=None, author_letter=None, source=None,
                            publish_date=None):
    """
    Return a list of dicts in form of the expected loading format. Can be
    potentially empty.

    :return: Dict
    """

    return_list: List[Dict] = list()
    _load_format = dict()
    # NO_COL = "NO_COLLECTION"

    if article_id:
        _load_format["id"] = article_id

    if title:
        _load_format["title"] = " ".join(title) \
            if isinstance(title, list) \
            else title

    if abstract:
        _load_format["abstract"] = " ".join(abstract) \
            if isinstance(abstract, list) \
            else abstract

    metadata = dict()
    if publish_date:
        metadata["publication_year"] = " ".join(publish_date) \
            if isinstance(publish_date, list) \
            else publish_date

    if author_letter:
        metadata["authors"] = " | ".join(author_letter) \
            if isinstance(author_letter, list) \
            else author_letter

    if source:
        metadata["journals"] = " ".join(source) \
            if isinstance(source, list) \
            else source

    if metadata:  # check if metadata obj is not empty
        _load_format["metadata"] = metadata

    if collection:
        if not isinstance(collection, list):
            collection = [collection]

        for _i in range(len(collection)):
            _col = collection[_i]
            _article = dict(_load_format)

            _article["collection"] = _col
            return_list.append(_article)

    return return_list


def my_time():
    return time.strftime('%H:%M:%S', time.gmtime(time.time() + 3600))


def main():
    start = time.time()

    print(f"[{my_time()}] Start translation...")
    files = get_json_files(PATH)
    print(f"[{my_time()}] {len(files)} files found to evaluate.")

    length = len(files)
    articles_by_col: Dict = dict()
    articles_list: List[Dict] = list()
    old_list = list()

    file_i = 0
    total_articles = 0

    running = True
    while running:
        lower_i = file_i * JSON_READS
        upper_i = lower_i + JSON_READS
        if upper_i > length:
            upper_i = length
            running = False

        print(f"[{my_time()}] Start reading from {lower_i} to {upper_i - 1}")

        for i in range(lower_i, upper_i):

            if i % int(length / 100) == 0:  # print percentage
                print(int(i / length * 100), "%")

            articles_list.extend(loading_format_from_file(files[i]))

        print(f"[{my_time()}] Finished reading files. Processing data now")

        for article in articles_list:
            col = article["collection"]

            if col not in articles_by_col:
                articles_by_col[col] = list()

            articles_by_col[col].append(article)

        print(f"[{my_time()}] Processing data finished.")

        for key in articles_by_col:
            filename = f"output/{key}_loading_format.json"
            file_exists = path.isfile(filename)
            old_list.clear()

            if file_exists:
                with open(filename) as _file:
                    old_list = json.load(_file)
                    _file.close()

            file = open(filename, "w")
            new_list = articles_by_col[key]
            old_list.extend(new_list)

            file.write(dumps(old_list))
            file.close()

            total_articles += len(new_list)

        articles_by_col.clear()
        articles_list.clear()
        file_i += 1

        print(f"[{my_time()}] Writing finished")

    end = time.time()

    print(f"[{my_time()}] Translation took {int((end - start) / 60)} minutes.")
    print(f"[{my_time()}] {total_articles} articles stored.")


if __name__ == '__main__':
    main()
