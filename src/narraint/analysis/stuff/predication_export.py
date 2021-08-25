import argparse
import logging

from sqlalchemy import or_

from narrant.entity.meshontology import MeSHOntology
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narrant.preprocessing.enttypes import CHEMICAL, DISEASE


def export_predication_core_as_tsv(output_file, document_collection, extraction_type):
    """
    Exports the predication as a tsv file with
    (doc_id, subject_id, relation, object_id)
    Converts MeSH Tree Numbers back to descriptors
    :param output_file: the output filename
    :param document_collection: the document collection
    :param extraction_type: the extraction type
    :return: None
    """
    session = SessionExtended.get()
    query = session.query(Predication).yield_per(1000000)
    query = query.filter(Predication.document_collection == document_collection)
    query = query.filter(Predication.extraction_type == extraction_type)
    query = query.filter(or_(Predication.subject_type == CHEMICAL, Predication.subject_type == DISEASE))
    query = query.filter(or_(Predication.object_type == CHEMICAL, Predication.object_type == DISEASE))
    mesh_ontology = MeSHOntology.instance()
    with open(output_file, 'wt') as f:
        f.write('document_id\tsubject_id\tpredicate\tobject_id')
        exported = set()
        for p in query:
            try:
                subject_desc = mesh_ontology.get_descriptor_for_tree_no(p.subject_id)[0]
                object_desc = mesh_ontology.get_descriptor_for_tree_no(p.object_id)[0]
                fields = (str(p.document_id), subject_desc, p.relation, object_desc)
                if fields not in exported:
                    f.write('\n' + '\t'.join(fields))
                    exported.add(fields)
            except KeyError:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("-c", "--collection", help="Document collection")
    parser.add_argument("-e", "--extraction", help="Extraction type to export")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Beginning export to tsv...')
    export_predication_core_as_tsv(args.output, args.collection, args.extraction)
    logging.info('Finished')


if __name__ == "__main__":
    main()
