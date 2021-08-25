import argparse
import logging

from sqlalchemy import and_

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narrant.entity.entityresolver import EntityResolver
from narraint.graph.labeled import LabeledGraph


def export_document_graph_as_dot(output_dot, document_id, document_collection):
    session = SessionExtended.get()
    #entity_resolver = EntityResolver.instance()
    query = session.query(Predication).filter(and_(Predication.document_id == document_id,
                                                   Predication.document_collection == document_collection))
   # query = query.filter(Predication.extraction_type == 'PathIE')

    graph = LabeledGraph()
    has_edge = False
    exported = set()
    translation = {}
    for pred in query:
        try:
            subject_id = pred.subject_id
            if subject_id not in translation:
                translation[pred.subject_id] = pred.subject_str
           # subject_id = entity_resolver.get_name_for_var_ent_id(pred.subject_id, pred.subject_type,
                                        #                         resolve_gene_by_id=False)
            predicate = pred.relation
            #object_id = entity_resolver.get_name_for_var_ent_id(pred.object_id, pred.object_type,
             #                                                   resolve_gene_by_id=False)
            object_id = pred.object_id
            if object_id not in translation:
                translation[object_id] = pred.object_str
            key = (subject_id, predicate, object_id)
            if key not in exported:
                exported.add(key)
                graph.add_edge(predicate, translation[subject_id], translation[object_id])
                has_edge = True
        except KeyError:
            pass
    if has_edge:
        graph.save_to_dot(output_dot)



def main():
   # parser = argparse.ArgumentParser()
 #   parser.add_argument("output")
  #  args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Beginning export document graph as dot file...')
    with open('ids.tsv', 'rt') as f:
        ids = set([int(li[:-1]) for li in f])
    for doc_id in ids:
        logging.info('Exporting document graph: {}'.format(doc_id))
        export_document_graph_as_dot('../../../data/document_graphs/{}.dot'.format(doc_id), doc_id, "trex")
    logging.info('Finished')


if __name__ == "__main__":
    main()
