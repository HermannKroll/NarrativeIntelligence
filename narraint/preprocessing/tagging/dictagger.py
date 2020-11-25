import os
import pickle
import re
from abc import ABCMeta, abstractmethod
from datetime import datetime

from sqlalchemy.testing.plugin.plugin_base import logging

from narraint.config import TMP_DIR, DICT_TAGGER_BLACKLIST
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.progress import print_progress_with_eta
from narraint.preprocessing.utils import get_document_id, DocumentError
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS


class Vocabulary:
    def __init__(self, short_name: str, long_name: str, version, tag_type,
                 index_cache: str, source_file: str, blacklist=None,
                 logger=None):
        self.short_name = short_name
        self.long_name = long_name
        self.version = version
        self.tag_type = tag_type
        self.index_cache = index_cache
        self.source_file = source_file
        self.blacklist = blacklist if blacklist else DICT_TAGGER_BLACKLIST

        self.desc_by_term = {}
        self.logger = logger if logger else logging

    def index_from_pickle(self):
        if os.path.isfile(self.index_cache):
            index = pickle.load(open(self.index_cache, 'rb'))
            if not isinstance(index, DictIndex):
                self.logger.warning('Ignore index: expect index file to contain an DosageFormTaggerIndexObject: {}'
                                    .format(self.index_cache))
                pass

            if index.tagger_version != self.version:
                self.logger.warning('Ignore index: index does not match tagger version ({} index vs. {} tagger)'
                                    .format(index.tagger_version, self.version))
                pass

            if index.source_file != self.source_file:
                self.logger.warning('Ignore index: index created with another source file ({} index vs. {} tagger)'
                                    .format(index.source_file, self.source_file))
                pass

            self.logger.debug('Use precached index from {}'.format(self.index_cache))
            self.desc_by_term = index.desc_by_term
            return index
        pass

    def get_blacklist_set(self):
        with open(self.blacklist) as f:
            blacklist = f.read().splitlines()
        blacklist_set = set()
        for s in blacklist:
            s_lower = s.lower()
            blacklist_set.add(s_lower)
            blacklist_set.add('{}s'.format(s_lower))
            blacklist_set.add('{}e'.format(s_lower))
            if s_lower.endswith('s') or s_lower.endswith('e'):
                blacklist_set.add(s_lower[0:-1])
        return blacklist_set

    def index_to_pickle(self):
        index = DictIndex(self.source_file, self.version)
        index.desc_by_term = self.desc_by_term
        if not os.path.isdir(TMP_DIR):
            os.mkdir(TMP_DIR)
        self.logger.debug('Storing DosageFormTagerIndex cache to: {}'.format(self.index_cache))
        pickle.dump(index, open(self.index_cache, 'wb+'))

    def prepare(self):
        if self.index_from_pickle():
            self.logger.info(f'{self.long_name} initialized from cache '
                             f'({len(self.desc_by_term.keys())} term mappings) - ready to start')
        else:
            self.create_index_from_source()
            blacklist_set = self.get_blacklist_set()
            self.desc_by_term = {k: v for k, v in self.desc_by_term.items() if k.lower() not in blacklist_set}
            self.index_to_pickle()

    def create_index_from_source(self):
        pass


class DictIndex:

    def __init__(self, source_file, tagger_version):
        self.source_file, self.tagger_version = source_file, tagger_version
        self.desc_by_term = {}


def get_n_tuples(in_list, n):
    for i, element in enumerate(in_list):
        if i + n <= len(in_list):
            yield in_list[i:i + n]
        else:
            break


def clean_vocab_word_by_split_rules(word: str) -> str:
    if word and re.match(r"[^\w]", word[0]):
        word = word[1:]
    if word and re.match(r"[^\w]", word[-1]):
        word = word[:-1]
    return word


def split_indexed_words(content):
    words = content.split(' ')
    ind_words = []
    next_index_word = 0
    for word in words:
        ind = next_index_word
        word_offset = 0
        if word and re.match(r"[^\w]", word[0]):
            word = word[1:]
            ind += 1
            word_offset += 1
        if word and re.match(r"[^\w]", word[-1]):
            word = word[:-1]
            word_offset += 1
        ind_words.append((word, ind))
        # index = last index + length of last word incl. offset
        next_index_word = next_index_word + len(word) + word_offset + 1
    return ind_words


class DictTagger(BaseTagger, metaclass=ABCMeta):
    PROGRESS_BATCH = 10000
    NAME = "DictionaryTagger"

    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_type = ()
        self.desc_by_term = {}
        self.log_file = os.path.join(self.log_dir, f"{DictTagger.NAME}.log")
        self.out_dir = os.path.join(self.root_dir, f"{DictTagger.NAME}_out")
        self.in_dir = os.path.join(self.root_dir, f"{DictTagger.NAME}_in")
        self.vocabs = {}

    def add_vocab(self, vocab: Vocabulary):
        if vocab.tag_type not in self.vocabs:
            self.vocabs[vocab.tag_type] = vocab
            return True
        else:
            return False

    # TODO: synchronization
    def prepare(self, resume=False):
        # TODO
        for _, vocab in self.vocabs.items():
            vocab.prepare()
        # Create output directory
        if not resume:
            os.mkdir(self.out_dir)
        else:
            raise NotImplementedError(f"Resuming {self.long_name} is not implemented.")

    def get_tags(self):
        return self._get_tags(self.out_dir)

    def run(self):
        skipped_files = []
        files_total = len(self.files)
        start_time = datetime.now()

        for idx, in_file in enumerate(self.files):
            if in_file.endswith(".txt"):
                out_file = os.path.join(self.out_dir, in_file.split("/")[-1])
                try:
                    self.tag(in_file, out_file)
                except DocumentError as e:
                    self.logger.debug("Error in document - will be skipped {}".format(in_file))
                    skipped_files.append(in_file)
                    self.logger.info(e)
                print_progress_with_eta(f"{self.long_name} tagging", self.get_progress(), files_total, start_time,
                                        print_every_k=self.PROGRESS_BATCH, logger=self.logger)
            else:
                self.logger.debug("Ignoring {}: Suffix .txt missing".format(in_file))

        end_time = datetime.now()
        self.logger.info("Finished in {} ({} files processed, {} files total, {} errors)".format(
            end_time - start_time,
            self.get_progress(),
            files_total,
            len(skipped_files)),
        )

    def tag(self, in_file, out_file):
        with open(in_file) as f:
            document = f.read()
        match = CONTENT_ID_TIT_ABS.match(document)
        if not match:
            raise DocumentError(f"No match in {in_file}")
        pmid, title, abstact = match.group(1, 2, 3)
        content = title.strip() + " " + abstact.strip()
        content = content.lower()

        # split into indexed single words
        ind_words = split_indexed_words(content)

        lines = []
        for spaces in range(self.config.dict_max_words):
            for word_tuple in get_n_tuples(ind_words, spaces + 1):
                words, indexes = zip(*word_tuple)
                term = " ".join(words)
                start = indexes[0]
                end = indexes[-1] + len(words[-1])
                hits = self.get_term(term)
                # print(f"Found {hits} for '{term}'")
                if hits:
                    for tagtype, descs in hits.items():
                        for desc in descs:
                            # remove white space between title and abstract
                            if start > len(title):
                                start = start - 1
                            line = "{id}\t{start}\t{end}\t{str}\t{type}\t{desc}\n".format(
                                id=pmid, start=start, end=end, str=term, type=tagtype,
                                desc=desc
                            )
                            lines.append(line)

        output = "".join(lines)
        # Write
        with open(out_file, "w") as f:
            f.write(output)

    def get_term(self, term):
        hits = {}
        for tagtype, vocab in self.vocabs.items():
            hit = vocab.desc_by_term.get(term)
            if hit:
                hits[tagtype] = hit
        return hits

    def get_progress(self):
        return len([f for f in os.listdir(self.out_dir) if f.endswith(".txt")])

    def get_successful_ids(self):
        """
        DictTagger doesn't include content in output files, so no id can be retrieved from them if no tags found.
        Also, {short_name}_in dir is deleted if finished. Because of that, the ids are looked up in the files in input_dir,
        mapping is done via file name.
        :return:
        """
        finished_filenames = os.listdir(self.out_dir)
        finished_ids = {get_document_id(os.path.join(self.input_dir, fn)) for fn in finished_filenames}

        return finished_ids
