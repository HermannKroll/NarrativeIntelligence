

class LibraryGraph(object):

    def __init__(self):
        self.tuples = []
        self.doc2tuples = {}
        self.doc_ids = set()
        self.sent_ids = set()
        self.predicates = set()
        self.predicate2enttypes = {}
        self.fact2docIDs = {}

        self.type_and_cid_to_span = {}

    def compute_keys_for_facts(self, facts):
        keys = []
        for f in facts:
            keys.append(frozenset(f))
        return keys

    def compute_support_for_fact(self, facts):
        # first compute keys for the facts
        fact_keys = self.compute_keys_for_facts(facts)
        supporting_doc_ids = set()
        first = True
        for f_key in fact_keys:
            # if some fact key is not in docs -> no support
            if f_key not in self.fact2docIDs:
                return 0
            # first
            if first:
                supporting_doc_ids.update(self.fact2docIDs[f_key])
                first = False
                continue

            # compute set intersection (both doc should support this)
            support_for_new = self.fact2docIDs[f_key]

            inter = supporting_doc_ids.intersection(support_for_new)
            # no support
            if len(inter) == 0:
                return 0
            # work with new intersection
            supporting_doc_ids = inter
        # return support for facts
        return len(supporting_doc_ids)

    def add_span_for_cid_and_type(self, cid, type, span):
        if type not in self.type_and_cid_to_span:
            self.type_and_cid_to_span[type] = {}
        if cid not in self.type_and_cid_to_span[type]:
            self.type_and_cid_to_span[type][cid] = [span]
        else:
            self.type_and_cid_to_span[type][cid] = span

    def add_tuple_for_doc(self, doc_id, tuple):
        if doc_id not in self.doc2tuples:
            self.doc2tuples[doc_id] = [tuple]
        else:
            self.doc2tuples[doc_id].append(tuple)

    def add_doc_for_fact(self, fact, doc_id):
        key = frozenset(fact)
        if key not in self.fact2docIDs:
            self.fact2docIDs[key] = set(doc_id)
        else:
            self.fact2docIDs[key].add(doc_id)

    def read_from_tsv(self, filename):
        first_line = True
        with open(filename, 'r') as f:
            for line in f:
                # skip first line
                if first_line:
                    first_line = False
                    continue
                line = line.replace('\n', '')
                split = line.split('\t')

                doc_id = split[0]
                sent_id = split[1]
                s_cid = split[3]
                s_span = split[4]
                s_type = split[5]
                predicate = split[6]
                o_cid = split[7]
                o_span = split[8]
                o_type = split[9]
                prob = split[10]

                if predicate not in self.predicates:
                    self.predicates.add(predicate)

                type_pair = (s_type, o_type)
                if predicate not in self.predicate2enttypes:
                    self.predicate2enttypes[predicate] = [type_pair]
                elif type_pair not in self.predicate2enttypes[predicate]:
                    self.predicate2enttypes[predicate].append(type_pair)

                t = (doc_id, s_cid, predicate, o_cid, prob)
                self.tuples.append(t)
                doc_t = (s_cid, predicate, o_cid)
                self.add_tuple_for_doc(doc_id, doc_t)

                self.add_doc_for_fact((s_cid, predicate, o_cid), doc_id)

                self.add_span_for_cid_and_type(s_cid, s_type, s_span)
                self.add_span_for_cid_and_type(o_cid, o_type, o_span)

                self.doc_ids.add(doc_id)
                self.sent_ids.add(sent_id)

        print('Read {} tuples from csv'.format(len(self.tuples)))


