import logging
from stories.library_graph import LibraryGraph
from graph.labeled import LabeledGraph



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

    def __compute_connectivity_components(self, doc2pg):
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

    def __longest_common_prefix(self, strs):
        if not strs:
            return ""
        for i, letter_group in enumerate(zip(*strs)):
            # ["flower","flow","flight"]
            # print(i,letter_group,set(letter_group))
            # 0 ('f', 'f', 'f') {'f'}
            if len(set(letter_group)) > 1:
                return strs[0][:i]
        else:
            return min(strs)


    def __compute_generalisation_costs(self, label1, label2, class_split_char='.', cost_per_step=1):
        if label1 == label2:
            return 0
        # compute common prefix
        prefix = self.__longest_common_prefix([label1, label2])
        # no overlap
        if len(prefix) == 0:
            return 0
        if len(label1) > len(label2):
            longest = label1
        else:
            longest = label2
        return (longest.count(class_split_char) - prefix.count(class_split_char)) * cost_per_step

    def mine_stories(self, min_fact_overlap_threshold):
        logging.info('Computing document pairs to check...')
        doc_amount = len(self.plot_lg.doc2factkeys.keys())
        doc_pairs_to_check = self.__compute_document_pairs(min_fact_overlap_threshold)
        logging.info('Need to check {} document pairs (instead of {})'.format(len(doc_pairs_to_check), doc_amount*doc_amount))

        logging.info('Constructing plot graphs....')
        doc2pg = {}
        for doc_id, facts in self.plot_lg.doc2facts.items():
            pg = self.construct_graph(facts)
            doc2pg[doc_id] = pg
            pg.save_to_dot('../data/dot/{}.dot'.format(doc_id))
        logging.info('Plot graphs constructed!')

        return

        logging.info('Merging plot graphs to narratives...')
        # go through all candidate pairs
        for d1, d2 in doc_pairs_to_check:
            pg1 = doc2pg[d1]
            pg2 = doc2pg[d2]

            matched_e1 = set()
            matched_e2 = set()
            matched_pairs = []

            for e1 in pg1.get_edges():
                s1, p1, o1 = e1.get_as_triple()
                for e2 in pg2.get_edges():
                    # skip matched edge
                    if e2 in matched_e2:
                        continue
                    s2, p2, o2 = e2.get_as_triple()
                    # cannot match them
                    if p1 != p2:
                        continue
                    # exact matches
                    if s1.get_label() == s2.get_label() and o1.get_label() == o2.get_label():
                        matched_pairs.append((e1, e2))
                        matched_e1.add(e1)
                        matched_e2.add(e2)
                        continue


            edit_candidates_for_edge = {}
            # not exactly matched yet
            for e1 in pg1.get_edges():
                if e1 in matched_e1:
                    continue
                s1, p1, o1 = e1.get_as_triple()
                for e2 in pg2.get_edges():
                    # skip matched edge
                    if e2 in matched_e2:
                        continue
                    s2, p2, o2 = e2.get_as_triple()
                    # predicates must be equal
                    if p1 != p2:
                        continue
                    # compute edit costs to generalize subject and object
                    edit_costs = self.__compute_generalisation_costs(s1.get_label(), s2.get_label())
                    edit_costs += self.__compute_generalisation_costs(o1.get_label(), o2.get_label())

                    t =  (e2, edit_costs)
                    if e1 not in edit_candidates_for_edge:
                        edit_candidates_for_edge[e1] = [t]
                    else:
                        edit_candidates_for_edge[e1].append(t)

            matched_pairs_with_edit = []
            # match for each edge the candidate with lowest costs
            for e1, cands in edit_candidates_for_edge.items():
                min_costs = cands[0][1]
                min_partner = cands[0][0]
                for c_e2, costs in cands:
                    if costs < min_costs:
                        min_partner = c_e2
                        min_costs = min_costs
                # partner with lowest cost matches
                matched_pairs_with_edit = [e1, min_partner]


        logging.info('Narratives computed!')



logging.basicConfig(format='%(levelname)s-%(asctime)s: %(message)s', level=logging.INFO)

lg = LibraryGraph()
#lg.read_from_tsv('../data/lg_pmc_sim_ami_108.tsv')
lg.read_from_tsv('../data/lg_pmc_8712.tsv')

miner = StoryMiner(lg)
#miner.mine_stories(0.01)
#miner.mine_stories(0.05)
miner.mine_stories(0.1)