import logging

from library_graph import LibraryGraph
from graph import LabeledGraph



class StoryMiner(object):

    def __init__(self, plot_library_graph):
        self.plot_lg = plot_library_graph

    def construct_graph(self, facts):
        plot_graph = LabeledGraph()
        for f in facts:
            s, p, o = f[0], f[1], f[2]
            plot_graph.add_edge(p, s, o)
        return plot_graph


    def compute_similarity(self, pg1, pg2):
        return 1.0

    def __compute_document_pairs(self, min_fact_overlap_threshold):
        doc_pairs_to_check = []
        for i1, (doc_id1, f_keys1) in enumerate(self.plot_lg.doc2factkeys.items()):
            for i2, (doc_id2, f_keys2) in enumerate(self.plot_lg.doc2factkeys.items()):
                # don't compare to yourself
                if doc_id1 == doc_id2:
                    continue
                # it's symmetric - don't check twice
                if i2 > i1:
                    continue

                intersection = f_keys1.intersection(f_keys2)
                inter_len = len(intersection)
                jaccard = len(intersection) / (len(f_keys1) + len(f_keys2) - inter_len)
                if jaccard > min_fact_overlap_threshold:
                    doc_pairs_to_check.append((doc_id1, doc_id2))
        return doc_pairs_to_check

    def mine_stories(self, min_fact_overlap_threshold):
        logging.info('Computing document pairs to check...')
        doc_amount = len(self.plot_lg.doc2factkeys.keys())
        doc_pairs_to_check = self.__compute_document_pairs(min_fact_overlap_threshold)
        logging.info('Need to check {} document pairs (instead of {})'.format(len(doc_pairs_to_check), doc_amount*doc_amount))

        logging.info('Constructing plot graphs....')
        doc2pg = {}
        for doc_id, facts in self.plot_lg.doc2facts.items():
            doc2pg[doc_id] = self.construct_graph(facts)
        logging.info('Plot graphs constructed!')

        logging.info('Counting connectivity components...')
        # count connectivity components
        connectivity_stats = {}
        for d, pg in doc2pg.items():
            con_comps = pg.compute_connectivity_components()
            amount = len(con_comps)
            if amount not in connectivity_stats:
                connectivity_stats[amount] = 1
            else:
                connectivity_stats[amount] += 1
        logging.info('Connectivity components counted!')
        logging.info(sorted(connectivity_stats.items(), key=lambda item: item[1], reverse=True))

        #for d1, pg1 in doc2pg.items():
        #    for d2, pg2 in doc2pg.items():
        #        # don't compare to yourself
        #        if d1 == d2:
        #            continue

         #       similarity = self.compute_similarity(pg1, pg2)


logging.basicConfig(format='%(levelname)s-%(asctime)s: %(message)s', level=logging.INFO)

lg = LibraryGraph()
lg.read_from_tsv('../data/lg_pmc_8712.tsv')

miner = StoryMiner(lg)
miner.mine_stories(0.1)