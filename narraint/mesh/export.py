from narraint.config import MESH_DESCRIPTORS_FILE
from narraint.mesh.data import MeSHDB


def export_mesh_subtrees_as_tsv(meshdb, tree_numbers, output_file):
    visited = set()
    nodes = []
    for tn in tree_numbers:
        header_node = meshdb.desc_by_tree_number(tn)
        child_nodes = meshdb.descs_under_tree_number(tn)

        nodes_in_tree = []
        # add header node
        if header_node.unique_id not in visited:
            nodes_in_tree.append(header_node)
            visited.add(header_node.unique_id)

        # go trough all nodes
        for node in child_nodes:
            if node.unique_id not in visited:
                nodes_in_tree.append(node)
                visited.add(node.unique_id)
        print('{} nodes added from subtree {}'.format(len(nodes_in_tree), tn))
        nodes.extend(nodes_in_tree)

    with open(output_file, 'w') as f:
        f.write('MESH Descriptor\tHeading\tTerms\n')
        for n in nodes:
            term_str = n.terms[0].string
            for t in n.terms[1:]:
                term_str += '; {}'.format(t.string)

            tree_str = n.tree_numbers[0]
            for t in n.tree_numbers[1:]:
                tree_str += '; {}'.format(t)

            f.write('MESH:{}\t{}\t{}\t{}\n'.format(n.unique_id, n.heading, term_str, tree_str))


DOSAGE_FORM_TREE_NUMBERS = ["D26.255", "E02.319.300", "J01.637.512.600", "J01.637.512.850", "J01.637.512.925"]

print('load mesh file...')
meshdb = MeSHDB.instance()
meshdb.load_xml(MESH_DESCRIPTORS_FILE)
print('beginning export...')
export_mesh_subtrees_as_tsv(meshdb, DOSAGE_FORM_TREE_NUMBERS, 'dosage_forms_dict2020.tsv')
print('export finished')
