import argparse
import os
import logging

from pubtator.document import TaggedDocument


def load_pubtator_file(pmid, pubtator_dir, prefix='PMC'):
    file_name = os.path.join(pubtator_dir, prefix+pmid+'.txt')
    doc = None
    with open(file_name, 'r') as f:
        doc = TaggedDocument(f.read())
    if not doc:
        raise Exception('PubTator document loading failed')
    return doc


def get_subject_and_object_entities(doc, sub, obj):
    # default not hit
    subs_included = []
    objs_included = []
    # compute lower case with empty spaces
    sub_text = ' {} '.format(sub.lower())
    obj_text = ' {} '.format(obj.lower())

    # check if an entity occurs within the sentence
    for ent in doc.tags:
        ent_txt = ' {} '.format(ent.text.lower())
        if ent_txt in sub_text:
            s_t = (ent_txt, ent.mesh, ent.type)
            subs_included.append(s_t)
        if ent_txt in obj_text:
            o_t = (ent_txt, ent.mesh, ent.type)
            objs_included.append(o_t)

    return subs_included, objs_included


def clean_open_ie(input, output, pubtator_dir, logger, pubtator_prefix='PMC'):
    logger.info('beginning cleaning step...')
    # tuples with just include tagged entities
    tuples_cleaned = []
    # cached pubtator docs
    pubtator_cache = {}
    # don't include the same tuple twice for a single sentence
    already_included = set()
    # open the input open ie file
    with open(input, 'r') as f:
        # read all lines for a single doc
        tuples_cached = []
        for line in f:
            components = line.strip().split("\t")
            pmid = components[0]
            subj = components[1]
            pred = components[2]
            obj = components[3]
            sent = components[4]
            tuples_cached.append((pmid, subj, pred, obj, sent))

        logger.info('{} OpenIE tuples read...'.format(len(tuples_cached)))
        logger.info('cleaning tuples...')
        i = 0
        len_tuples = len(tuples_cached)
        # go trough all cached triples
        for pmid, subj, pred, obj, sent in tuples_cached:
            # is pubtator doc cached? if not load it
            if pmid not in pubtator_cache:
                pubtator_cache[pmid] = load_pubtator_file(pmid, pubtator_dir, prefix=pubtator_prefix)
            pubtator_doc = pubtator_cache[pmid]

            # go trough all detected entities in the subject and object part of the open ie triple
            sub_ents, obj_ents = get_subject_and_object_entities(pubtator_doc, subj, obj)
            for s_txt, s_id, s_type in sub_ents:
                for o_txt, o_id, o_type in obj_ents:
                    # check if tuple is already extracted for sentence
                    key = frozenset((pmid, s_id, o_id, pred, sent))
                    if key not in already_included:
                        t = (pmid, subj, pred, obj, sent, s_id, s_txt, s_type, o_id, o_txt, o_type)
                        tuples_cleaned.append(t)
                        already_included.add(key)

            if i % 10000 == 0:
                progress = i * 100 / len_tuples
                print("progress: %d%%   \r" % progress, end='')
            i += 1

        logger.info('cleaning finished...')

    logger.info('writing results...')
    with open(output, "w") as f:
        f.write("\n".join('\t'.join(t) for t in tuples_cleaned))
    logger.info('results written')




def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='OpenIE export file')
    parser.add_argument("pubtator_dir", help='Directory of pubtator files')
    parser.add_argument("output", help='Cleaned OpenIE export file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    clean_open_ie(args.input, args.output, args.pubtator_dir, logger)


if __name__ == "__main__":
    main()
