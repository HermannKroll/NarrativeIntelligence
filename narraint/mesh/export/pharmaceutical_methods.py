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

    relevant_descs = []
    for desc in meshdb.get_all_descs():
        for tn in desc.tree_numbers:
            if tn.startswith('E'):
                relevant_descs.append(desc)
                break

    logging.info(f'beginning export of {len(relevant_descs)} descriptors...')
    with open('pharmaceutical_methods_2021.tsv', 'w') as f:
        f.write('MeSH Tree\tMeSH Descriptor\tHeading\tTerms\n')
        for d in relevant_descs:
            # get all synonyms
            term_str = d.terms[0].string
            for t in d.terms[1:]:
                term_str += '; {}'.format(t.string)

            for tn in d.tree_numbers:
                if tn[0] in PM_TREE_NUMBERS_TO_KEEP:  # hand-crafted rules to keep tree numbers
                    f.write('{}\tMESH:{}\t{}\t{}\n'.format(tn, d.unique_id, d.heading, term_str))

    logging.info('export finished')


if __name__ == "__main__":
    main()
