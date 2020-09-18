import argparse
import logging
from operator import and_

import pandas as pd
from collections import defaultdict

from mlxtend.frequent_patterns import apriori
from mlxtend.preprocessing import TransactionEncoder
from sqlalchemy import or_

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.entity.enttypes import GENE, SPECIES


def get_facts_for_document_collection(document_collection):
    """
    queries the predication table and
    retrieves a dictionary mapping a document id to a set of facts in it
    :param document_collection: the document collection is used as a filter
    :return: a dict mapping a document id to a set of facts in it
    """
    logging.info('Retrieving facts for collection: {}'.format(document_collection))
    session = Session.get()
    q = session.query(Predication.document_id, Predication.subject_id, Predication.subject_type,
                      Predication.predicate_canonicalized,
                      Predication.object_id, Predication.object_type).yield_per(100000)\
        .filter_by(document_collection=document_collection).filter(Predication.predicate_canonicalized.isnot(None))\
        .filter(Predication.predicate_canonicalized != 'associated')\
        .filter(Predication.predicate_canonicalized != 'PRED_TO_REMOVE')\
        .filter(and_(Predication.subject_type != "Species", Predication.object_type != "Species"))\
        .filter(Predication.subject_id != Predication.object_id)

    doc2facts = defaultdict(set)
    fact_count = 0
    for res in q:
        d_id, s, s_t, p, o, o_t = res[0], res[1], res[2], res[3], res[4], res[5]
        if s_t == SPECIES:
            s = 'S:' + s
        if s_t == GENE:
            s = 'G:' + s
        if o_t == SPECIES:
            o = 'S:' + o
        if o_t == GENE:
            o = 'G:' + o

        doc2facts[d_id].add((s, p, o))
        fact_count += 1

    logging.info('{} facts for {} documents retrieved'.format(fact_count, len(doc2facts)))
    return doc2facts


def frequent_item_set_mining(doc2facts, output):
    transformed_list = []
    for doc, facts in doc2facts.items():
        transaction = []
        for s, p, o in facts:
            transaction.append(('{}<{}>{}'.format(s, p, o)))
        transformed_list.append(transaction)

    te = TransactionEncoder()
    te_ary = te.fit(transformed_list).transform(transformed_list)
    df = pd.DataFrame(te_ary, columns=te.columns_)
    frequent_itemsets = apriori(df, min_support=0.0005, use_colnames=True, low_memory=True)
    frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
    doc_count = len(doc2facts)
    frequent_itemsets['documents'] = frequent_itemsets['support'].apply(lambda x: int(x * doc_count))
    print(frequent_itemsets)
    frequent_itemsets.to_csv(output, sep='\t')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("collection", help='document collection to mine common fact patterns')
    parser.add_argument("output", help='resulting file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    doc2facts = get_facts_for_document_collection(args.collection)
    frequent_item_set_mining(doc2facts, args.output)


if __name__ == "__main__":
    main()