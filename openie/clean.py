import argparse
import os
import logging


from openie.pubtator import PubTatorDoc


def load_pubtator_file(pmid, pubtator_dir, prefix='PMC'):
    file_name = os.path.join(pubtator_dir, prefix+pmid+'.txt')
    doc = PubTatorDoc()
    doc.load_from_file(file_name)
    return doc


def get_subject_and_object_entity(pubtator_doc, sub, obj):
    sub_included = None
    sub_id = None
    sub_type = None
    obj_included = None
    obj_id = None
    obj_type = None
    for anno in pubtator_doc.annotations:
        if sub.lower() == anno[2].lower() or anno[2].lower() in sub.lower():
            sub_included = anno[2].lower()
            sub_id = anno[4]
            sub_type = anno[3]
        if obj.lower() == anno[2].lower() or anno[2].lower() in obj.lower():
            obj_included = anno[2].lower()
            obj_id = anno[4]
            obj_type = anno[3]

    return sub_included, sub_id, sub_type, obj_included, obj_id, obj_type


def clean_open_ie(input, output, pubtator_dir,logger, pubtator_prefix='PMC'):
    logger.info('beginning cleaning step...')
    # tuples with just include tagged entities
    tuples_cleaned = []
    # cached pubtator docs
    pubtator_cache = {}
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
        # go trough all cached triples
        for pmid, subj, pred, obj, sent in tuples_cached:
            # is pubtator doc cached? if not load it
            if pmid not in pubtator_cache:
                pubtator_cache[pmid] = load_pubtator_file(pmid, pubtator_dir, prefix=pubtator_prefix)
            pubtator_doc = pubtator_cache[pmid]

            sub_ent, sub_id, sub_type, obj_ent, obj_id, obj_type = get_subject_and_object_entity(pubtator_doc, subj, obj)
            if sub_ent and obj_ent:
                t = (pmid, subj, pred, obj, sent, sub_id, sub_ent, sub_type, obj_id, obj_ent, obj_type)
                tuples_cleaned.append(t)

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
