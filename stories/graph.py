import copy

class LabeledNode(object):

    def __init__(self, label):
        self.__edges_out = []
        self.__edges_in = []
        self.__label = label

    def add_edge_outgoing(self, edge):
        self.__edges_out.append(edge)

    def add_edge_incoming(self, edge):
        self.__edges_in.append(edge)

    def get_edges_outgoing(self):
        return self.__edges_out

    def get_edges_incoming(self):
        return self.__edges_in

    def get_label(self):
        return self.__label

    def __str__(self):
        return self.__label


class LabeledEdge(object):

    def __init__(self, label, node1, node2):
        self.__label = label
        self.__node1 = node1
        self.__node2 = node2

    def get_node1(self):
        return self.__node1

    def get_node2(self):
        return self.__node2

    def get_label(self):
        return self.__label

    def __str__(self):
        return '{} - {} -> {}'.format(self.__node1, self.__label, self.__node2)


class LabeledGraph(object):

    def __init__(self):
        self.nodes = {}
        self.edges = []

    def get_node(self, label):
        if label in self.nodes:
            return self.nodes[label]
        return None

    def add_edge(self, label, node1_label, node2_label):
        if node1_label not in self.nodes:
            node1 = LabeledNode(node1_label)
            self.nodes[node1_label] = node1
        else:
            node1 = self.nodes[node1_label]

        if node2_label not in self.nodes:
            node2 = LabeledNode(node2_label)
            self.nodes[node2_label] = node2
        else:
            node2 = self.nodes[node2_label]

        edge = LabeledEdge(label, node1, node2)
        node1.add_edge_outgoing(edge)
        node2.add_edge_incoming(edge)
        self.edges.append(edge)

    def breath_search(self, start_node, max_steps=-1):
        current_step = 0
        todo = [start_node]
        visited = set()
        visited_edges = set()
        target_graph = LabeledGraph()
        if max_steps == 0:
            return target_graph

        # as long as their are non discovered nodes
        while todo:
            next_iteration = []
            # iterate over current stack
            while todo:
                node = todo.pop()
                # skip visited nodes
                if node in visited:
                    continue
                visited.add(node.get_label())

                # append all neighbours to next iteration
                for e in node.get_edges_outgoing():
                    if e in visited_edges:
                        continue
                    visited_edges.add(e)

                    node2 = e.get_node2()
                    # add all outgoing edges to target graph
                    target_graph.add_edge(e.get_label(), e.get_node1().get_label(), node2.get_label())
                    # add only nodes not visited yet
                    if node2.get_label() not in visited:
                        next_iteration.append(node2)
                for e in node.get_edges_incoming():
                    if e in visited_edges:
                        continue
                    visited_edges.add(e)

                    node1 = e.get_node1()
                    # add all outgoing edges to target graph
                    target_graph.add_edge(e.get_label(), node1.get_label(), e.get_node2().get_label())
                    # add only nodes not visited yet
                    if node1.get_label() not in visited:
                        next_iteration.append(node1)

            current_step += 1
            # check if max steps are enabled - stop if max steps are reached
            if current_step >= max_steps > 0:
                break
            # prepare next iteration
            todo.extend(next_iteration)

        return target_graph

    def compute_connectivity_components(self):
        if len(self) == 0:
            return None
        if len(self) == 1:
            return self
        # connectivity components
        components = []
        # put first element to queue
        todo = []
        todo.extend(self.nodes.values())
        # visited nodes
        visited = set()
        # while there are nodes not discovered yet
        while todo:
            node = todo.pop()
            # skip visited nodes
            if node.get_label() in visited:
                continue
            visited.add(node.get_label())

            # start a breath search for this node
            component = self.breath_search(node)
            # add all nodes visited here to our already visited nodes
            visited.update(component.nodes.keys())
            # component found
            components.append(component)

        return components

    def __len__(self):
        return len(self.edges)

    def __str__(self):
        return ''.join([str(e) + '\n' for e in self.edges])

class GraphTools(object):

    @staticmethod
    def find_largest_common_subgraphdfdg(node1, node2):
        g1Node2EdgesInc = {}
        g1Node2EdgesOut = {}
        g2Node2EdgesIn = {}
        g2Node2EdgesOut = {}



    @staticmethod
    def find_largest_common_subgraph(node1, node2):
        todo = [(node1, node2, LabeledGraph(), set())]
        subgraph_candidates = []

        # while pairs to check in list
        while todo:
            n1, n2, subg, visited = todo.pop()
            changed = False

            branch_later = []
            # check all outgoing and all incoming edges
            edges_to_check = [(n1.get_edges_outgoing(), n2.get_edges_outgoing()), (n1.get_edges_incoming(), n2.get_edges_incoming())]
            # check if their are more pairs in neighbourhood
            for mode, edge_list_pair in enumerate(edges_to_check):
                for i, e1 in enumerate(edge_list_pair[0]):
                    cands_for_e1 = []
                    for j, e2 in enumerate(edge_list_pair[1]):
                        # skip already visited combis
                        key = frozenset((e1, e2))
                        if key in visited:
                            continue

                        # it's symmetric - just check once
                        if i > j:
                            continue
                        # edge labels are similar?
                        if e1.get_label() == e2.get_label():
                            # outgoing edges
                            if mode == 0:
                                cands_for_e1.append((e1.get_node2(), e2.get_node2(), key))
                            # incoming edges
                            else:
                                cands_for_e1.append((e1.get_node1(), e2.get_node1(), key))

                    # check all candidates for e1
                    for n1_next, n2_next, key in cands_for_e1:
                        if mode == 0:
                            new_n1_label = n1.get_label() + '|' + n2.get_label()
                            new_n2_label = n1_next.get_label() + '|' + n2_next.get_label()
                        else:
                            new_n2_label = n1.get_label() + '|' + n2.get_label()
                            new_n1_label = n1_next.get_label() + '|' + n2_next.get_label()
                        # add it as an edge to our graph
                        # easy? only one candidate? No branching!
                        if len(cands_for_e1) == 1:
                            visited.add(key)
                            subg.add_edge(e1.get_label(), new_n1_label, new_n2_label)
                            todo.append((n1_next, n2_next, subg, visited))
                            changed = True
                        else:
                            branch_later.append((e1, n1_next, new_n1_label, n2_next, new_n2_label, key))

            # check in next run
            for e1, n1_next, new_n2_label, n2_next, new_n2_label, key in branch_later:
                # we have to check multiple combinations and have to branch here
                copy_subg = copy.deepcopy(subg)
                visited_c = copy.deepcopy(visited)
                visited_c.add(key)
                copy_subg.add_edge(e1.get_label(), new_n1_label, new_n2_label)
                todo.append((n1, n2, copy_subg, visited_c))
                changed = True

            if not changed:
                subgraph_candidates.append(subg)

        max_sub = None
        max_sub_len = -1
        for current_sub in subgraph_candidates:
            current_len = len(current_sub)
            if current_len > max_sub_len:
                max_sub_len = current_len
                max_sub = current_sub

        return max_sub



    @staticmethod
    def find_largest_common_subgraphsdfasf(graph1, graph2):
        max_sub = None
        max_sub_len = -1
        for i, n1 in enumerate(graph1.nodes.values()):
            for j, n2 in enumerate(graph2.nodes.values()):
                # the problem is symmetric - just check the half matrix
                if i > j:
                    continue

                for current_sub in GraphTools.find_common_subgraph(n1, n2):
                    current_len = len(current_sub)
                    if current_len > max_sub_len:
                        max_sub_len = current_len
                        max_sub = current_sub

        return max_sub
