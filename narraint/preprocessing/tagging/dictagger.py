import copy
import os
import pickle
import re
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from datetime import datetime

from typing import List

from narraint.config import TMP_DIR, DICT_TAGGER_BLACKLIST
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.progress import print_progress_with_eta
from narraint.preprocessing.utils import get_document_id, DocumentError
from narraint.pubtator.document import TaggedDocument, TaggedEntity
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS


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

    # For cases like "water-induced" add "water"
    amendment = []
    for word, index in ind_words:
        split = word.split("-")
        if len(split) == 2 and split[1][-2:] == "ed":
            amendment.append((split[0], index))
    ind_words += amendment
    return ind_words



class DictTagger(BaseTagger, metaclass=ABCMeta):
    PROGRESS_BATCH = 10000

    def __init__(self, short_name, long_name, version, tag_types, index_cache, source_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_types = [tag_types,]
        self.short_name, self.long_name, self.version = short_name, long_name, version
        self.index_cache = index_cache
        self.source_file = source_file
        self.desc_by_term = {}
        self.log_file = os.path.join(self.log_dir, f"{short_name}.log")
        self.out_dir = os.path.join(self.root_dir, f"{short_name}_out")
        self.in_dir = os.path.join(self.root_dir, f"{short_name}_in")

    def get_types(self):
        return self.tag_types

    def _index_from_pickle(self):
        if os.path.isfile(self.index_cache):
            with open(self.index_cache, 'rb') as f:
                index = pickle.load(f)
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

    def _index_to_pickle(self):
        index = DictIndex(self.source_file, self.version)
        index.desc_by_term = self.desc_by_term
        if not os.path.isdir(TMP_DIR):
            os.mkdir(TMP_DIR)
        self.logger.debug('Storing DosageFormTagerIndex cache to: {}'.format(self.index_cache))
        pickle.dump(index, open(self.index_cache, 'wb+'))

    @abstractmethod
    def _index_from_source(self):
        pass

    @staticmethod
    def get_blacklist_set():
        with open(DICT_TAGGER_BLACKLIST) as f:
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

    # TODO: synchronization
    def prepare(self, resume=False):
        if self._index_from_pickle():
            self.logger.info(f'{self.long_name} initialized from cache '
                             f'({len(self.desc_by_term.keys())} term mappings) - ready to start')
        else:
            self._index_from_source()
            blacklist_set = DictTagger.get_blacklist_set()
            self.desc_by_term = {k: v for k, v in self.desc_by_term.items() if k.lower() not in blacklist_set}
            self._index_to_pickle()
        # Create output directory
        os.makedirs(self.out_dir, exist_ok=True)


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
                    self._tag(in_file, out_file)
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

    def tag_doc(self, in_doc:TaggedDocument) -> TaggedDocument:
        """
        Generate tags for a TaggedDocument
        :param in_doc: document containing title+abstract to tag. Is modified by adding tags
        :return: the modified in_doc
        """
        abb_vocab = dict()
        out_doc = in_doc
        pmid, title, abstact = in_doc.id, in_doc.title, in_doc.abstract
        content = title.strip() + " " + abstact.strip()
        content = content.lower()

        # split into indexed single words
        ind_words = split_indexed_words(content)

        tags = []
        for spaces in range(self.config.dict_max_words):
            for word_tuple in get_n_tuples(ind_words, spaces + 1):
                words, indexes = zip(*word_tuple)
                term = " ".join(words)
                start = indexes[0]
                end = indexes[-1] + len(words[-1])
                if start > len(title):
                    start = start - 1
                hits = list(self.generate_tagged_entities(end, pmid, start, term))
                tags += hits
                if hits:
                    match = re.match(r" \((\w*)\).*", content[indexes[-1]+len(words[-1]):])
                    if match:
                        abbreviation = match.groups()[0]
                        abb_vocab[abbreviation] = [(t.ent_type, t.ent_id) for t in hits]

        if abb_vocab:
            for spaces in range(self.config.dict_max_words):
                for word_tuple in get_n_tuples(ind_words, spaces + 1):
                    words, indexes = zip(*word_tuple)
                    term = " ".join(words)
                    start = indexes[0]
                    end = indexes[-1] + len(words[-1])
                    if start > len(title):
                        start = start - 1
                    hits = list(self.generate_tagged_entities(end, pmid, start, term, abb_vocab))
                    tags += hits

        if self.config.dict_check_abbreviation:
            tags = DictTagger.clean_abbreviation_tags(tags, self.config.dict_min_full_tag_len)

        out_doc.tags += tags
        return out_doc

    def _tag(self, in_file, out_file):
        with open(in_file) as f:
            document = f.read()
        result = self.tag_doc(TaggedDocument(document))
        with open(out_file, "w+") as f:
            f.write(str(result))

    def generate_tag_lines(self, end, pmid, start, term):
        hits = self._get_term(term)
        # print(f"Found {hits} for '{term}'")
        if hits:
            for desc in hits:
                yield pmid, start, end, term, self.tag_types[0], desc

    def generate_tagged_entities(self, end, pmid, start, term, tmp_vocab = None):
        hits = set()
        if tmp_vocab:
            tmp_hit = tmp_vocab.get(term)
            if tmp_hit:
                hits |= {hit[1] for hit in tmp_hit}
        else:
            hits |= set(self._get_term(term))

        # print(f"Found {hits} for '{term}'")
        if hits:
            for desc in hits:
                yield TaggedEntity((pmid, start, end, term, self.tag_types[0], desc))

    def _get_term(self, term):
        hits = self.desc_by_term.get(term)
        return hits if hits else set()

    @staticmethod
    def clean_abbreviation_tags(tags: List[TaggedEntity], minimum_tag_len=5):
        """
        This method removes all tags which are assumed to be an abbreviation and which do not have a long expression
        within the document
        e.g. Aspirin (ASA) -> ASA is allowed in the document because Aspirin is associated with the same descriptor
        without aspirin ASA will further not be kept as a valid tag
        :param minimum_tag_len: the minimum tag length to treat a term as a 'full' tag
        :param tags: a list of tags
        :return: a list of cleaned tags
        """
        tags_cleaned = []
        desc2tags = defaultdict(list)
        for t in tags:
            desc2tags[t.ent_id].append(t)

        # search if a full tag is found for a descriptor
        for desc, tags in desc2tags.items():
            keep_desc = False
            for t in tags:
                if len(t.text) >= minimum_tag_len:
                    keep_desc = True
                    break
            if keep_desc:
                tags_cleaned.extend(tags)
        return tags_cleaned

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
