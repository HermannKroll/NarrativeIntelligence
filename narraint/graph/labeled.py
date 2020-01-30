import hashlib


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
        """
        gets a node of this graph by label
        :param label: label of node
        :return: a node or none if no node is found
        """
        if label in self.nodes:
            return self.nodes[label]
        return None

    def add_edge(self, label, node1_label, node2_label):
        """
        adds a edge and nodes to the graph
        :param label: label of edge
        :param node1_label: label of node from
        :param node2_label: label of node to
        :return: nothing
        """

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

    def breath_first_search(self, start_node, max_steps=-1):
        """
        applies a breath first search starting by a node
        :param start_node: starting node
        :param max_steps: how many steps should be done? -1 if unlimited
        :return: a subgraph
        """
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
        """
        computes all connectivity components in this graph
        :return: a list of subgraphs
        """
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
            component = self.breath_first_search(node)
            # add all nodes visited here to our already visited nodes
            visited.update(component.nodes.keys())
            # component found
            components.append(component)

        return components

    def __len__(self):
        return len(self.edges)

    def __str__(self):
        return ''.join([str(e) + '\n' for e in self.edges])

    def save_to_dot(self, filename):
        def get_node_id(node_obj):
            return "n{}".format(hashlib.sha1(node_obj.get_label().encode("UTF-8")).hexdigest()[:10])

        with open(filename, "w") as f:
            f.write("digraph g {\n")

            for label, node in self.nodes.items():
                f.write("    {} [label=\"{}\"];\n".format(get_node_id(node), label))

            for edge in self.edges:
                f.write("    {} -> {} [label=\"{}\"];\n".format(
                    get_node_id(edge.get_node1()), get_node_id(edge.get_node2()), edge.get_label()))

            f.write("}\n")
