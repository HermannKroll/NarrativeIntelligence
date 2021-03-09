import logging

from narraint.config import MESH_DESCRIPTORS_FILE
from narraint.mesh.data import MeSHDB

METHODS_QUALIFIER = 'Q000379'


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info('load mesh file...')
    meshdb: MeSHDB = MeSHDB.instance()
    meshdb.load_xml(MESH_DESCRIPTORS_FILE)

    relevant_descs = []
    for desc in meshdb.get_all_descs():
        for q in desc.allowable_qualifiers_list:
            if q.qualifier_ui == METHODS_QUALIFIER:
                relevant_descs.append(desc)

    logging.info(f'beginning export of {len(relevant_descs)} descriptors...')
    with open('pharmaceutical_methods_2021.tsv', 'w') as f:
        f.write('MeSH Tree\tMeSH Descriptor\tHeading\tTerms\n')
        for d in relevant_descs:
            # get all synonyms
            term_str = d.terms[0].string
            for t in d.terms[1:]:
                term_str += '; {}'.format(t.string)

            for tn in d.tree_numbers:
                f.write('{}\tMESH:{}\t{}\t{}\n'.format(tn, d.unique_id, d.heading, term_str))

    logging.info('export finished')


if __name__ == "__main__":
    main()
