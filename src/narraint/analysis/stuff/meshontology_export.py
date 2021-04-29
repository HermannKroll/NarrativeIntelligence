import argparse
import logging

from narraint.entity.meshontology import MeSHOntology


def export_mesh_ontology_to_tsv(output):
    """
    Exports the MeSH ontology as a tsv file
    Descriptor SuperDescriptor are the lines
    :param output: the output filename
    :return: None
    """
    ontology = MeSHOntology().instance()
    with open(output, 'wt') as f:
        f.write('entity\tentity')
        exported = set()
        for tn, desc in ontology.treeno2desc.items():
            if '.' in tn:
                tn_superclass = '.'.join(tn.split('.')[:-1])
                superclass_desc = ontology.get_descriptor_for_tree_no(tn_superclass)
                key = (desc[0], superclass_desc[0])
                if key not in exported:
                    f.write('\n{}\t{}'.format(desc[0], superclass_desc[0]))
                    exported.add(key)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Beginning export to tsv...')
    export_mesh_ontology_to_tsv(args.output)
    logging.info('Finished')


if __name__ == "__main__":
    main()
