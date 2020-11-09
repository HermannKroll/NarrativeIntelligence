import json
from unittest import TestCase

from spacy.lang.en import English

from narraint.extraction.extraction_utils import filter_document_sentences_without_tags
from narraint.extraction.pathie.main import load_and_fix_json_nlp_data, \
    pathie_reconstruct_sentence_sequence_from_nlp_output, pathie_find_tags_in_sentence, \
    pathie_reconstruct_text_from_token_indexes, pathie_find_relations_in_sentence
from narraint.tests.test_config import get_test_resource_filepath


class ExtractionUtilsTestCase(TestCase):

    def test_find_relations_in_sentences(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        test_pubtator = get_test_resource_filepath("pathie/sample_collection.pubtator")
        doc2sentences, doc2tags = filter_document_sentences_without_tags(26, test_pubtator, nlp)

        for doc_id in doc2sentences:
            json_path = get_test_resource_filepath(f"pathie/jsons/{doc_id}.txt.json")
            json_data = load_and_fix_json_nlp_data(json_path)
            for idx, sent in enumerate(json_data["sentences"]):
                sent_string = pathie_reconstruct_sentence_sequence_from_nlp_output(sent["tokens"]).lower()
                relations = pathie_find_relations_in_sentence(sent["tokens"], sent_string)
#                print(relations)



    def test_find_tags_in_sentences(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        test_pubtator = get_test_resource_filepath("pathie/sample_collection.pubtator")
        doc2sentences, doc2tags = filter_document_sentences_without_tags(26, test_pubtator, nlp)

        self.assertEqual(16, len(doc2sentences))
        self.assertEqual(16, len(doc2tags))

        for doc_id in doc2sentences:
            json_path = get_test_resource_filepath(f"pathie/jsons/{doc_id}.txt.json")
            json_data = load_and_fix_json_nlp_data(json_path)

            for idx, sent in enumerate(json_data["sentences"]):
                tags_found = pathie_find_tags_in_sentence(sent["tokens"], doc2tags[doc_id])
                for tag, tag_indexes in tags_found:
                    reconstructed_tag = pathie_reconstruct_text_from_token_indexes(sent["tokens"], tag_indexes)
                    tag_s = tag.text.lower().strip()
                    reconstructed_tag_s = reconstructed_tag.lower().strip()
                    if tag_s != reconstructed_tag_s:
                        print(f'Reconstructed tag does not match: "{tag_s}" != "{reconstructed_tag_s}" ')

    def test_reconstruct_sentences(self):
        nlp = English()  # just the language with no model
        sentencizer = nlp.create_pipe("sentencizer")
        nlp.add_pipe(sentencizer)

        test_pubtator = get_test_resource_filepath("pathie/sample_collection.pubtator")
        doc2sentences, doc2tags = filter_document_sentences_without_tags(26, test_pubtator, nlp)

        self.assertEqual(16, len(doc2sentences))
        self.assertEqual(16, len(doc2tags))

        for doc_id in doc2sentences:
            json_path = get_test_resource_filepath(f"pathie/jsons/{doc_id}.txt.json")
            json_data = load_and_fix_json_nlp_data(json_path)

            if len(json_data["sentences"]) != len(doc2sentences[doc_id]):
                print(f'Does not match sentence length: {len(json_data["sentences"])} != {len(doc2sentences[doc_id])}')
                continue

            for idx, sent in enumerate(json_data["sentences"]):
                reconstructed_sentence = pathie_reconstruct_sentence_sequence_from_nlp_output(sent["tokens"])
                if doc2sentences[doc_id][idx].strip() != reconstructed_sentence.strip():
                    print(f'Does not match:')
                    print(f'"{doc2sentences[doc_id][idx].strip()}"')
                    print('!=')
                    print(f'"{reconstructed_sentence.strip()}"')


