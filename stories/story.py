import copy
import itertools
import gzip
import time

from library_graph import LibraryGraph
from mesh.data import MeSHDB


#class Graph(object):


class GraphQuery(object):

    def __init__(self):
        self.entities = set()
        self.facts = set()

    def add_fact(self, subject, predicate, object):
        if not subject or not predicate or not object:
            print('Do not support empty subject, predicate or object as a fact ({},{},{})'.
                  format(subject, predicate, object))
        self.entities.add(subject)
        self.entities.add(object)
        self.facts.add((subject, predicate, object))


class GraphQueryProcessor(object):

    def check_variable_substitution(self, substitutions, variable, substitution):
        # if variable has currently no substitution
        if variable not in substitution:
            # substitution works fine
            return True
        else:
            # substitution must be checked, whether it fits or not
            for sub in substitutions[variable]:
                if sub == substitution:
                    # compatible substitution - everything works
                    return True
            # no compatible substitution was found - no query result
            return False

    def add_var_substitution(self, var_subs, var, sub):
        if var not in var_subs:
            var_subs[var] = set()
        var_subs[var].add(sub)

    def match_query_facts_in_doc_facts(self, query_facts, doc_facts):
        """
        matches a set of query facts with variables against the document store
        :param query_facts: a set of query facts (allowed variables starting with ?, i.e., ?x)
        :param doc_facts: a set of document facts to check against
        :return: True if facts can be matched to document, the hashmap of variable substitutions
        """
        # store a dictionary of possible variable substitutions
        var_subs = {}
        # all query facts must match
        for qf in query_facts:
            var_subs_for_fact = {}
            # allow variables in query
            if qf[0].startswith('?') or qf[2].startswith('?'):
                has_substitution = False
                # look if var is already substituted
                for df in doc_facts:
                    # predicates are equal?
                    if qf[1] == df[1]:
                        # then q1 is now substituted by - check it
                        if qf[0].startswith('?') and self.check_variable_substitution(var_subs, qf[0], df[0]):
                            # if q2 is also a variable - add substitution or check
                            if qf[2].startswith('?'):
                                if self.check_variable_substitution(var_subs_for_fact, qf[2], df[2]):
                                    self.add_var_substitution(var_subs_for_fact, qf[0], df[0])
                                    self.add_var_substitution(var_subs_for_fact, qf[2], df[2])
                                    has_substitution = True
                            else:
                                # qf2 is not a variable - just check if equal
                                if qf[2] == df[2]:
                                    self.add_var_substitution(var_subs_for_fact, qf[0], df[0])
                                    has_substitution = True
                                    # then q1 is now substituted by - check it
                        # only if qf is not a varible, else it would be checked above
                        elif qf[2].startswith('?') and self.check_variable_substitution(var_subs, qf[2], df[2]):
                            # qf0 is not a variable - just check if equal
                            if qf[0] == df[0]:
                                self.add_var_substitution(var_subs_for_fact, qf[2], df[2])
                                has_substitution = True

                # no substitution was found?
                if not has_substitution:
                    return False, {} # no query result found
                # merge var_subs for this fact against all var subs and check for compatibility
                if len(var_subs_for_fact) > 0:  # some var is substituted
                    # go through all new substituted variables
                    for k, v in var_subs_for_fact.items():
                        # check whether variable is already substituted
                        if k in var_subs:
                            # compute intersection
                            inter = set(v).intersection(var_subs[k])
                            # no intersection between both subs? Then there cannot be a query result
                            if len(inter) == 0:
                                return False, {}
                            # intersection represents the var subs now
                            var_subs[k] = inter
                        else:
                            # just add it
                            var_subs[k] = v
            else:
                # just check whether there is a direct match
                # here no substitution is necessary
                if qf not in doc_facts:
                    return False, {}

        # check with variable combinations are compatible to each other
        if len(var_subs) > 1:
            combinations = []
            v_names = []
            for var, subs in var_subs.items():
                v_names.append(var)
                combinations.append(list(subs))
            # cross product of lists
            combinations = list(itertools.product(*combinations))
            # check which combination is correct
            correct_var_combinations = {}
            for comb in combinations:
                # test if comb is valid
                comb_valid = True
                # check which combination fits
                for qf in query_facts:
                    s, p, o = qf[0], qf[1], qf[2]
                    # replace each variable in fact
                    for i in range(0, len(v_names)):
                        # replace vars in fact
                        if qf[0] == v_names[i]:
                            s = comb[i]
                        if qf[2] == v_names[i]:
                            o = comb[i]
                    qf_copy = (s, p, o)
                    # test whether fact is in doc_facts
                    if qf_copy not in doc_facts:
                        # if a single fact is not included - this combination is not valid
                        comb_valid = False
                        break
                # just add valid combinations
                if comb_valid:
                    for i in range(0, len(v_names)):
                        self.add_var_substitution(correct_var_combinations, v_names[i], comb[i])

            # if no comb is valid - no query result
            if len(correct_var_combinations) == 0:
                return False, {}
            return True, correct_var_combinations
        else:
            return True, var_subs


class StoryEntityTagger(object):

    def tag_entity(self, word):
        pass

    def get_tagger_name(self):
        pass


class StoryProcessor(object):
    def __init__(self, library_graph, entity_taggers=[]):
        self.library_graph = library_graph
        self.graph_query_processor = GraphQueryProcessor()
        self.entity_taggers = entity_taggers

    def add_entity_tagger(self, entity_tagger):
        self.entity_taggers.append(entity_tagger)

    def match_graph_query(self, graph_query, debug=False):
        """
        matches a graph query against the document fact store
        :param graph_query: a graph query allowing variables
        :param debug: should print additional debug information?
        :return: a list of tuples consisting of (doc_id, variable_substitutions (HashMap))
        """
        matched_docs = []
        # go through all documents
        for doc_id, doc_fs in self.library_graph.doc2tuples.items():
            # now match query against this facts
            matched, subs = self.graph_query_processor.match_query_facts_in_doc_facts(graph_query, doc_fs)
            if matched:
                if debug:
                    print('Matched in doc {} with var_subs {}'.format(doc_id, subs))
                matched_docs.append((doc_id, subs))
        return matched_docs

    def _score_graph_pattern(self, graph_pattern):
        return 1.0

    def translate_keywords_to_graph_queries(self, keyword_query, k):
        # split keyword query in single words
        words = keyword_query.split(' ')

        # if keyword query is empty - skip it
        if not keyword_query or len(words) == 0:
            return []

        # store all detected entities in this query
        entities_detected = []
        other_words = []
        # go through all words
        for w in words:
            # default entity
            if w.startswith('\"') and w.endswith('\"'):
                if w.startswith('"C'):
                    # is a disease
                    e_type = 'Disease'
                elif w.startswith('"D'):
                    # is a chemical / drug
                    e_type = 'Chemical'
                else:
                    # its a gene
                    e_type = 'Gene'
                entities_detected.append((w[1:-1], w[1:-1], e_type, 'Manual'))
                continue

            for entity_tagger in self.entity_taggers:
                # is the word a entity?
                ent_id, ent_type = entity_tagger.tag_entity(w)
                if ent_id:
                    entities_detected.append((w, ent_id, ent_type, entity_tagger.get_tagger_name()))
                else:
                    other_words.append(w)

        # we try to match all words now against predicates with a string similarity
        predicates_detected = []
        not_matched_words = []
        for w in other_words:
            if w in self.library_graph.predicates:
                predicates_detected.append(w)
            else:
                not_matched_words.append(w)

        # start with just one empty query
        stack = [[]]
        # try to match predicate between tuples
        for pred in predicates_detected:
            # get pred types from library graph
            for pred_type_pair in self.library_graph.predicate2enttypes[pred]:
                candidates_pos_0 = []
                candidates_pos_1 = []
                for _, e_id, e_type, _ in entities_detected:
                    if e_type == pred_type_pair[0]:
                        candidates_pos_0.append(e_id)
                        continue
                    if e_type == pred_type_pair[1]:
                        candidates_pos_1.append(e_id)
                        continue
                # no combination possible
                if len(candidates_pos_0) == 0 or len(candidates_pos_1) == 0:
                    continue

                # stories for next generation
                stack_copy = []
                # compute cross product of candidates
                cand_pairs = list(itertools.product(candidates_pos_0, candidates_pos_1))
                # go through all pairs of candidates
                for cand_p in cand_pairs:
                    t = (cand_p[0], pred, cand_p[1])
                    # extend query list by new tuple
                    for graph_query in stack:
                        # append same pattern
                        if len(graph_query) > 0:
                            # only if it is not the empty story
                            stack_copy.append(graph_query)
                        # expand pattern and append it also
                        graph_query_c = copy.copy(graph_query)
                        graph_query_c.append(t)
                        stack_copy.append(graph_query_c)

                stack = stack_copy

        # construct possible graph queries
        graph_queries = []

        # select best stories here
        for gp in stack:

            supp = self.library_graph.compute_support_for_fact(gp)
            print('Support {} for story {}'.format(supp, gp))

        graph_queries = stack

        # return the list of final graph queries
        return graph_queries

    def query(self, keyword_query, amount_of_stories=5):
        start = time.time()
        # 1. transform the keyword query to a graph query
        # multiple solutions are possible
        graph_queries = self.translate_keywords_to_graph_queries(keyword_query, k=amount_of_stories)

        query_trans_time = time.time() - start
        before_matching = time.time()

        # 2. compute matches to graph query on document level
        results = []
        for gq in graph_queries:
            doc_ids = self.match_graph_query(gq)
            results.append((gq, doc_ids))

        query_matched_time = time.time() - before_matching
        complete_time = time.time() - start
        print('='*120)
        print('='*120)
        print('Time needed: {}s ({}s Query Translation / {}s Matching)'.format(complete_time, query_trans_time, query_matched_time))
        print('='*120)
        print('='*120)
        # returns a list of doc_ids
        return results


class MeshTagger(StoryEntityTagger):
    def __init__(self, meshdb):
        self.meshdb = meshdb

    def tag_entity(self, word):
        descs = self.meshdb.descs_by_name(word)
        if descs:
            for d in descs:
                if d.heading == word:
                    if d.tree_number.startswith('C'):
                        return "MESH:{}".format(d.unique_id), 'Disease'
                    if d.tree_number.startswith('D'):
                        if d.tree_number.startswith('D08'):
                            return "MESH:{}".format(d.unique_id), 'Gene'
                        else:
                            return "MESH:{}".format(d.unique_id), 'Chemical'

        return None, None

    def get_tagger_name(self):
        return 'Mesh 2019 Tagger'


class GeneTagger(StoryEntityTagger):
    def __init__(self, ctd_genes_file):
        self.gene2id = {}
        with gzip.open(ctd_genes_file, 'r') as f:
            for l in f:
                line = str(l).replace('b\'', '')
                # skip comments
                if line.startswith('#'):
                    continue
                # print(line)
                comp = line.replace('\\n', '').split('\\t')
                # print(comp)
                gene_id = comp[2]
                gene_name = comp[1]

                self.gene2id[gene_name] = gene_id

        print('Amount of gene ids: {}'.format(len(self.gene2id)))

    def tag_entity(self, word):
        if word in self.gene2id:
            return self.gene2id[word], 'Gene'
        return None, None

    def get_tagger_name(self):
        return 'CTD Gene Tagger'

