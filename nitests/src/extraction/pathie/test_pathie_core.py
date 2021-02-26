from unittest import TestCase

from narraint.extraction.pathie.core import PathIEToken, pathie_reconstruct_sentence_sequence_from_tokens, \
    pathie_reconstruct_text_from_token_indexes, pathie_find_tags_in_sentence, pathie_find_relations_in_sentence, \
    PathIEDependency, pathie_extract_facts_from_sentence
from narraint.pubtator.document import TaggedEntity


class TestPathIECore(TestCase):

    def setUp(self) -> None:
        self.test_sentence = "This is a test"
        self.test_tokens = [PathIEToken("This", "this", "", " ", 1, 0, 4, "", ""),
                            PathIEToken("is", "is", " ", " ", 2, 6, 7, "V", "be"),
                            PathIEToken("a", "a", " ", " ", 3, 9, 9, "", ""),
                            PathIEToken("test", "test", " ", " ", 4, 10, 14, "", "")]

        self.test_tags = [TaggedEntity(start=0, end=4, text="this", ent_type="Drug", ent_id="1"),
                          TaggedEntity(start=10, end=14, text="test", ent_type="Drug", ent_id="2")]

        self.test_2_sentence = "This looks like a test"
        self.test_2_tokens = [PathIEToken("This", "this", "", " ", 1, 0, 4, "", ""),
                              PathIEToken("looks", "looks", " ", " ", 2, 6, 10, "V", "look"),
                              PathIEToken("like", "like", " ", " ", 3, 11, 15, "", "like"),
                              PathIEToken("a", "a", " ", " ", 3, 16, 16, "", ""),
                              PathIEToken("test", "test", " ", " ", 4, 18, 22, "", "")]

        self.test_2_tags = [TaggedEntity(start=0, end=4, text="this", ent_type="Drug", ent_id="1"),
                            TaggedEntity(start=18, end=22, text="test", ent_type="Disease", ent_id="2")]
        self.test_2_dependencies = [PathIEDependency(1, 2, "X"),
                                    PathIEDependency(2, 4, "X")]

        self.test_2_dependencies_with_look = [PathIEDependency(1, 2, "X"),
                                              PathIEDependency(2, 3, "X"),
                                              PathIEDependency(3, 4, "X")]

    def test_reconstruct_sentence(self):
        sentence = self.test_sentence
        tokens = self.test_tokens
        reconstructed_sentence = pathie_reconstruct_sentence_sequence_from_tokens(tokens)
        self.assertEqual(sentence, reconstructed_sentence)

        sentence = "!This, is, a test!"
        tokens = [PathIEToken("This", "this", "!", ",", 1, 0, 4, "", ""),
                  PathIEToken("is", "is", " ", ",", 2, 6, 7, "", ""),
                  PathIEToken("a", "a", " ", " ", 3, 9, 9, "", ""),
                  PathIEToken("test", "test", " ", "!", 4, 10, 14, "", "")]

        reconstructed_sentence = pathie_reconstruct_sentence_sequence_from_tokens(tokens)
        self.assertEqual(sentence, reconstructed_sentence)

    def test_reconstruct_text_from_token_indexes(self):
        tokens = self.test_tokens
        token_indexes = [1]
        reconstructed_sentence = pathie_reconstruct_text_from_token_indexes(tokens, token_indexes)
        self.assertEqual("This", reconstructed_sentence)

        token_indexes = [1, 3, 4]
        reconstructed_sentence = pathie_reconstruct_text_from_token_indexes(tokens, token_indexes)
        self.assertEqual("This a test", reconstructed_sentence)

        token_indexes = [1, 2, 3, 4]
        reconstructed_sentence = pathie_reconstruct_text_from_token_indexes(tokens, token_indexes)
        self.assertEqual("This is a test", reconstructed_sentence)

        token_indexes = [4]
        reconstructed_sentence = pathie_reconstruct_text_from_token_indexes(tokens, token_indexes)
        self.assertEqual("test", reconstructed_sentence)

        token_indexes = [3]
        reconstructed_sentence = pathie_reconstruct_text_from_token_indexes(tokens, token_indexes)
        self.assertEqual("a", reconstructed_sentence)

    def test_pathie_find_tags_in_sentence(self):
        tags_with_tokens = pathie_find_tags_in_sentence(self.test_tokens, self.test_tags)
        tag, tokens = tags_with_tokens[0]
        self.assertEqual(tag, self.test_tags[0])
        self.assertEqual(tokens, [1])

        tag, tokens = tags_with_tokens[1]
        self.assertEqual(tag, self.test_tags[1])
        self.assertEqual(tokens, [4])

    def test_pathie_find_relations_in_sentence(self):
        vidx2text_and_lemma = pathie_find_relations_in_sentence(self.test_tokens, self.test_sentence.lower())
        # ignore be
        self.assertEqual(0, len(vidx2text_and_lemma))

        vidx2text_and_lemma = pathie_find_relations_in_sentence(self.test_2_tokens, self.test_2_sentence.lower())
        # extract look
        self.assertEqual(1, len(vidx2text_and_lemma))
        self.assertEqual(vidx2text_and_lemma[2], ('looks', 'look'))

    def test_pathie_find_relations_in_sentence_keywords(self):
        vidx2text_and_lemma = pathie_find_relations_in_sentence(self.test_2_tokens, self.test_2_sentence.lower(),
                                                                important_keywords=["like"])
        # extract look
        self.assertEqual(2, len(vidx2text_and_lemma))
        self.assertEqual(vidx2text_and_lemma[2], ('looks', 'look'))
        self.assertEqual(vidx2text_and_lemma[3], ('like', 'like'))

    def test_pathie_find_relations_in_sentence_phrases(self):
        vidx2text_and_lemma = pathie_find_relations_in_sentence(self.test_2_tokens, self.test_2_sentence.lower(),
                                                                important_phrases=["looks like"])
        self.assertEqual(2, len(vidx2text_and_lemma))
        self.assertEqual(vidx2text_and_lemma[2], ('looks like', 'look like'))
        self.assertEqual(vidx2text_and_lemma[3], ('looks like', 'look like'))

    def test_pathie_extract_facts_from_sentence(self):
        extractions = pathie_extract_facts_from_sentence(0, self.test_2_tags, self.test_2_tokens,
                                                         self.test_2_dependencies)
        self.assertEqual(1, len(extractions))
        ext = extractions[0]
        self.assertEqual(0, ext.document_id)
        self.assertEqual("1", ext.subject_id)
        self.assertEqual("Drug", ext.subject_type)
        self.assertEqual("this", ext.subject_str)
        self.assertEqual("2", ext.object_id)
        self.assertEqual("Disease", ext.object_type)
        self.assertEqual("looks", ext.predicate)
        self.assertEqual("look", ext.predicate_lemmatized)

    def test_pathie_extract_facts_from_sentence_with_not_connected_keywords(self):
        # Like should not effect the extraction because its not connected
        extractions = pathie_extract_facts_from_sentence(0, self.test_2_tags, self.test_2_tokens,
                                                         self.test_2_dependencies, important_keywords=["like"])
        self.assertEqual(1, len(extractions))
        ext = extractions[0]
        self.assertEqual(0, ext.document_id)
        self.assertEqual("1", ext.subject_id)
        self.assertEqual("Drug", ext.subject_type)
        self.assertEqual("this", ext.subject_str)
        self.assertEqual("2", ext.object_id)
        self.assertEqual("Disease", ext.object_type)
        self.assertEqual("looks", ext.predicate)
        self.assertEqual("look", ext.predicate_lemmatized)

    def test_pathie_extract_facts_from_sentence_with_connected_keywords(self):
        # Like should not effect the extraction because its not connected
        extractions = pathie_extract_facts_from_sentence(0, self.test_2_tags, self.test_2_tokens,
                                                         self.test_2_dependencies_with_look,
                                                         important_keywords=["like"])
        self.assertEqual(2, len(extractions))
        ext = extractions[0]
        self.assertEqual(0, ext.document_id)
        self.assertEqual("1", ext.subject_id)
        self.assertEqual("Drug", ext.subject_type)
        self.assertEqual("this", ext.subject_str)
        self.assertEqual("2", ext.object_id)
        self.assertEqual("Disease", ext.object_type)
        self.assertEqual("looks", ext.predicate)
        self.assertEqual("look", ext.predicate_lemmatized)

        ext = extractions[1]
        self.assertEqual(0, ext.document_id)
        self.assertEqual("1", ext.subject_id)
        self.assertEqual("Drug", ext.subject_type)
        self.assertEqual("this", ext.subject_str)
        self.assertEqual("2", ext.object_id)
        self.assertEqual("Disease", ext.object_type)
        self.assertEqual("like", ext.predicate)
        self.assertEqual("like", ext.predicate_lemmatized)

    def test_pathie_extract_facts_from_sentence_with_phrase(self):
        extractions = pathie_extract_facts_from_sentence(0, self.test_2_tags, self.test_2_tokens,
                                                         self.test_2_dependencies, important_phrases=["looks like"])
        self.assertEqual(1, len(extractions))
        ext = extractions[0]
        self.assertEqual(0, ext.document_id)
        self.assertEqual("1", ext.subject_id)
        self.assertEqual("Drug", ext.subject_type)
        self.assertEqual("this", ext.subject_str)
        self.assertEqual("2", ext.object_id)
        self.assertEqual("Disease", ext.object_type)
        self.assertEqual("looks like", ext.predicate)
        self.assertEqual("look like", ext.predicate_lemmatized)

