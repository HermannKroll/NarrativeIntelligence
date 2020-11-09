import logging
import os
from datetime import datetime

from narraint.progress import print_progress_with_eta
from narraint.pubtator.document import TaggedDocument
from narraint.pubtator.extract import read_pubtator_documents


def filter_document_sentences_without_tags(doc_len: int, input_file: str, spacy_nlp):
    """
    Filtering a PubTator file as a preperation for the extraction
    Keeps only sentences with at least two entities
    :param doc_len: the len of included documents in the input file
    :param input_file: a PubTator input file / directory of PubTator file
    :param spacy_nlp:
    :return: len of extracted documents, a dict mapping document ids to tags (ent_id, ' ' + lower(ent_str), ent_type)
    """
    logging.info('Filtering {} documents (keep only document sentences with tags)'.format(doc_len))
    doc2tags = dict()
    doc2sentences = dict()
    start_time = datetime.now()
    for idx, pubtator_content in enumerate(read_pubtator_documents(input_file)):
        print_progress_with_eta('filtering documents...', idx, doc_len, start_time, print_every_k=100)
        tagged_doc = TaggedDocument(pubtator_content, spacy_nlp=spacy_nlp)
        doc_id = tagged_doc.id

        filtered_content = []
        tag_terms = set()
        tag_original_character_offset = 0

        sorted_sentences = sorted(tagged_doc.sentence_by_id.keys())
        for sent in sorted_sentences:
            tags = tagged_doc.entities_by_sentence[sent]
            ent_ids = {t.ent_id for t in tags}
            if len(ent_ids) > 1:  # at minimum two tags must be included in this sentence
                sentence_str = tagged_doc.sentence_by_id[sent].text + ' '
                sentence_str_lower = sentence_str.lower()
                for t in tagged_doc.entities_by_sentence[sent]:
                    t_start_new = tag_original_character_offset + sentence_str_lower.index(t.text.lower())
                    t_start_end = t_start_new + len(t.text)
                    tag_terms.add((t.ent_id, t.text, t_start_new, t_start_end))

                tag_original_character_offset += len(sentence_str)
                filtered_content.append(sentence_str)

        # skip empty documents
        if not filtered_content:
            continue

        doc2sentences[doc_id] = filtered_content
        doc2tags[doc_id] = tag_terms

    return doc2sentences, doc2tags


def filter_and_write_documents_to_tempdir(doc_len: int, input_file: str, output_dir: str,
                                          out_filelist_file: str, spacy_nlp):
    """
    Filtering a PubTator file as a preperation for the extraction
    Keeps only sentences with at least two entities
    :param doc_len: the len of included documents in the input file
    :param input_file: a PubTator input file / directory of PubTator file
    :param output_dir: output directory where the documents are extracted
    :param out_filelist_file: output file where a filelist of all extracted files is stored
    :param spacy_nlp:
    :return: len of extracted documents, a dict mapping document ids to tags (ent_id, ' ' + lower(ent_str), ent_type)
    """
    logging.info('Filtering {} documents (keep only document sentences with tags)'.format(doc_len))
    amount_skipped_files = 0
    openie_files = []
    doc2sentences, doc2tags = filter_document_sentences_without_tags(doc_len, input_file, spacy_nlp)
    start_time = datetime.now()
    for idx, (doc_id, doc_sentences) in enumerate(doc2sentences.items()):
        # write filtered document
        o_file_path = os.path.join(output_dir, '{}.txt'.format(doc_id))
        openie_files.append(o_file_path)
        with open(o_file_path, 'w') as f_out:
            f_out.write(''.join(doc_sentences))
        print_progress_with_eta('writing documents...', idx, doc_len, start_time, print_every_k=10)

    logging.info('{} files need to be processed. {} files skipped.'.format(len(openie_files), amount_skipped_files))
    with open(out_filelist_file, "w") as f:
        f.write("\n".join(openie_files))
    return len(openie_files), doc2tags