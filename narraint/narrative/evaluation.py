from narraint.pubtator.document import TaggedDocument


def get_sentence_ratio_with_tags(tagged_doc):
    last_idx = 0
    sentences = []
    for s in tagged_doc.content.split(". "):
        sentences.append((last_idx, last_idx + len(s) - 1))
        last_idx += len(s)

    sentences_copy = sentences.copy()
    for idx, (start, end) in enumerate(sentences):
        for tag in tagged_doc.tags:
            if start <= tag.start <= end:
                sentences_copy[idx] = None

    n_sentences = len(sentences)
    n_sentences_without_tags = len([x for x in sentences_copy if x is not None])
    n_sentences_with_tags = n_sentences - n_sentences_without_tags
    return n_sentences, n_sentences_with_tags, round(float(n_sentences_with_tags / n_sentences), 2)


def evaluate_tagged_sentence_ratio(docs_strings):
    ratios = []
    for d in docs_strings:
        if d:
            doc = TaggedDocument(d)
            ratios.append(get_sentence_ratio_with_tags(doc)[2])
    return round(float(sum(ratios) / len(ratios)), 2)
