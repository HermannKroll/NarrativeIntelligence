import argparse
import itertools
import logging
from typing import Dict, Tuple, Any

from sqlalchemy import delete

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, Tag, SchemaSupportGraphInfo, BULK_QUERY_CURSOR_COUNT_DEFAULT

CO_OCCURRENCE_RELATION = 'co_occurred'


class SchemaSupportGraph:
    __instance = None

    @staticmethod
    def instance():
        if SchemaSupportGraph.__instance is None:
            SchemaSupportGraph()
        return SchemaSupportGraph.__instance

    def __init__(self):
        if SchemaSupportGraph.__instance is not None:
            raise Exception('This class is a singleton - use SchemaSupportGraph.instance()')
        else:
            self.spo2support = {}
            self.relations = set()
            self.entity_types = set()
            self.load_schema_graph_from_db()
            SchemaSupportGraph.__instance = self

    def load_schema_graph_from_db(self):
        """
        Loads the schema graph from the DB table
        :return: None
        """
        logging.info('Loading schema graph info from DB...')
        session = SessionExtended.get()

        query = session.query(SchemaSupportGraphInfo)
        for row in query:
            key = (row.subject_type, row.relation, row.object_type)
            self.spo2support[key] = row.support
            self.relations = row.relation
            self.entity_types.add(row.subject_type)
            self.entity_types.add(row.object_type)

        logging.info('Schema support graph load')

    def get_support(self, subject_type, relation, object_type):
        """
        Returns how many documents contain a (s, p, o) tuple
        :param subject_type: the subject entity type
        :param relation: the relation
        :param object_type: the object entity type
        :return: the support or 0 if (s, p, o) does not have support
        """
        if (subject_type, relation, object_type) in self.spo2support:
            return self.spo2support[(subject_type, relation, object_type)]
        else:
            return 0

    def get_relations_between(self, subject_type, object_type) -> Dict[str, int]:
        """
        Returns a dict mapping possible relations between (s, o) to their support values
        :param subject_type: the subject entity type
        :param object_type: the object entity type
        :return: a dict mapping possible relations between (s, o) to their support values
        """
        relation2frequency = {}
        for (s, p, o), support in self.spo2support.items():
            if s == subject_type and o == object_type:
                relation2frequency[p] = support
        return relation2frequency

    @staticmethod
    def compute_graph_for_predications():
        """
        Computes the graph schema info based on the Predication table
        Iterates over (collection, docid, subject_type, relation, object_type) tuples
        Counts how many documents support a certain (s, p, o) tuple
        :return: a dict mapping (s, p, o) tuples to their support values (int)
        """
        session = SessionExtended.get()
        logging.info('Counting predication entries...')
        p_count_query = session.query(Predication.document_collection, Predication.document_id,
                                      Predication.subject_type, Predication.relation, Predication.object_type)

        p_count_query = p_count_query.distinct()
        p_count = p_count_query.count()
        logging.info(f'Iterating over {p_count} predication table entries...')
        pred_query = session.query(Predication.document_collection, Predication.document_id,
                                   Predication.subject_type, Predication.relation, Predication.object_type)

        # Sort is important here to support the work with a buffer
        pred_query = pred_query.order_by(Predication.subject_type, Predication.relation, Predication.object_type)

        # Distinct to minimize the overhead
        pred_query = pred_query.distinct()

        pred_query = pred_query.yield_per(BULK_QUERY_CURSOR_COUNT_DEFAULT * 10)

        progress = Progress(total=p_count, print_every=1000, text="Iterating over predications")
        progress.start_time()

        # Find the support for every spo combination
        spo2support = {}
        # Buffer things
        doc_buffer = set()
        last_spo_key = None
        for idx, r in enumerate(pred_query):
            progress.print_progress(idx)

            spo_key = (r.subject_type, r.relation, r.object_type)
            if idx == 0:
                last_spo_key = spo_key

            if spo_key != last_spo_key:
                # We found a new spo key, so store the old one
                spo2support[last_spo_key] = len(doc_buffer)
                doc_buffer.clear()

            # Add the current document to the next buffer
            last_spo_key = spo_key
            doc_key = (r.document_collection, r.document_id)
            doc_buffer.add(doc_key)

        # Insert last values
        if len(doc_buffer) > 0:
            spo2support[last_spo_key] = len(doc_buffer)

        progress.done()

        return spo2support

    @staticmethod
    def compute_graph_for_tags():
        """
        Computes the support values of entity type co-occurrences in documents via the
        Tag table. Iterates over the Tab table and then computes the cross-product
        between entity types co-occurring in the same document
        :return:
        """
        session = SessionExtended.get()
        logging.info('Count tag entries...')
        t_count_query = session.query(Tag.document_collection, Tag.document_id, Tag.ent_type)
        t_count_query = t_count_query.distinct()

        t_count = t_count_query.count()
        logging.info(f'Iterating over {t_count} tag table entries...')
        tag_query = session.query(Tag.document_collection, Tag.document_id, Tag.ent_type)
        tag_query = tag_query.order_by(Tag.document_collection, Tag.document_id)
        tag_query = tag_query.distinct()

        tag_query = tag_query.yield_per(BULK_QUERY_CURSOR_COUNT_DEFAULT * 100)

        progress = Progress(total=t_count, print_every=1000, text="Iterating over tags")
        progress.start_time()
        spo2docs = {}
        last_doc = None
        last_doc_entity_types = set()
        for idx, r in enumerate(tag_query):
            progress.print_progress(idx)
            doc_key = (r.document_collection, r.document_id)
            if idx == 0:
                last_doc = doc_key

            # Find all entity types for a document
            if doc_key != last_doc:
                # There is a new document incoming
                # Compute cross product between entity types
                # add co-occurrence relation between these types
                for et1, et2 in itertools.product(last_doc_entity_types, last_doc_entity_types):
                    spo = (et1, CO_OCCURRENCE_RELATION, et2)
                    if spo not in spo2docs:
                        spo2docs[spo] = set()

                    spo2docs[spo].add(doc_key)

                # New document does not have any types yet
                last_doc_entity_types.clear()

            # We found our new document
            last_doc_entity_types.add(r.ent_type)
            last_doc = doc_key

        # Add last remaining values
        if len(last_doc_entity_types) > 0:
            # add co-occurrence relation between these types
            for et1, et2 in itertools.product(last_doc_entity_types, last_doc_entity_types):
                spo = (et1, CO_OCCURRENCE_RELATION, et2)
                if spo not in spo2docs:
                    spo2docs[spo] = set()

                spo2docs[spo].add(last_doc)

        # convert document ids to a support number (just count)
        spo2support = {k: len(v) for k, v in spo2docs.items()}
        return spo2support

    @staticmethod
    def insert_spo2support_values(spo2support):
        """
        Inserts dicts mapping (s, p, o) values to support ints into the DB table
        :param spo2support: a dict mapping (s, p, o) to their support values
        :return: None
        """
        logging.info(f'Inserting {len(spo2support)} spo2support values in database...')
        session = SessionExtended.get()

        values = []
        for spo, support in spo2support.items():
            values.append(dict(subject_type=spo[0],
                               relation=spo[1],
                               object_type=spo[2],
                               support=support))

        SchemaSupportGraphInfo.bulk_insert_values_into_table(session, values)

    @staticmethod
    def compute_schema_graph():
        """
        Computes the schema graph
        :return: None
        """
        logging.info('Deleting SchemaSupportGraphInfo database table...')
        session = SessionExtended.get()
        session.execute(delete(SchemaSupportGraphInfo))

        logging.info('Begin commit...')
        session.commit()
        logging.info('Committed.')

        #  SchemaSupportGraph.insert_spo2support_values(SchemaSupportGraph.compute_graph_for_tags())
        SchemaSupportGraph.insert_spo2support_values(SchemaSupportGraph.compute_graph_for_predications())


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    SchemaSupportGraph.compute_schema_graph()


if __name__ == "__main__":
    main()
