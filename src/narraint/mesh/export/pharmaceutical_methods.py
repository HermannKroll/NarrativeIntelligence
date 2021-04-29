import logging

from narraint.config import MESH_DESCRIPTORS_FILE
from narraint.mesh.data import MeSHDB

METHODS_QUALIFIER = 'Q000379'
PM_TREE_NUMBERS_TO_KEEP = ['E']


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info('load mesh file...')
    meshdb: MeSHDB = MeSHDB.instance()
    meshdb.load_xml(MESH_DESCRIPTORS_FILE)

    logging.info('beginning export of descriptors...')
    with open('pharmaceutical_methods_2021.tsv', 'w') as f:
        f.write('MeSH Descriptor\tHeading\tMeSH Tree\tTerms\n')
        for d in meshdb.get_all_descs():
            has_correct_tree = False
            for tn in d.tree_numbers:
                if tn.startswith('E'):
                    has_correct_tree = True
                    break
            # ignore descriptor
            if not has_correct_tree:
                continue
            # get all synonyms
            term_str = d.terms[0].string
            for t in d.terms[1:]:
                term_str += '; {}'.format(t.string)

            tree_str = None
            for t in d.tree_numbers:
                if t.startswith('E'):
                    if tree_str:
                        tree_str += '; {}'.format(t)
                    else:
                        tree_str = t

            f.write('{}\t{}\t{}\t{}\n'.format(d.unique_id, d.heading, tree_str, term_str))

    logging.info('export finished')


if __name__ == "__main__":
    main()
