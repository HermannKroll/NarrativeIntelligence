import argparse
import os
import pickle

from frontend.frontend.settings import base as settings
from mesh.data import MeSHDB


def build_index():
    db = MeSHDB.instance()
    db.load_xml(settings.DESCRIPTOR_FILE, True, True)
    with open(settings.MESHDB_INDEX, "wb") as f:
        pickle.dump(db.get_index(), f)


def mesh_synonyms(tree_number_list, output):
    def write(filename, lines):
        with open(filename, "w") as f:
            for fields in lines:
                f.write("MESH:{}\t{}\t{}\n".format(*fields))

    db = MeSHDB.instance()
    db.load_xml(settings.DESCRIPTOR_FILE, verbose=True)

    descendants_by_desc = dict()
    for tree_number in tree_number_list:
        print("Querying descriptors for {}".format(tree_number))
        desc = db.desc_by_tree_number(tree_number)
        descendants_by_desc[desc] = [desc] + db.descs_under_tree_number(tree_number)

    print("Collecting data ...")
    lines_by_desc = dict()
    for desc, descendants in descendants_by_desc.items():
        lines_by_desc[desc] = [(d.unique_id, d.heading, ", ".join(t.string for t in d.terms)) for d in descendants]

    print("Writing output ...")
    for desc, lines in lines_by_desc.items():
        write(os.path.join(output, "Descriptors_{}.tsv".format(desc.heading.replace(" ", "_"))), lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--mesh-synonyms", nargs="+", metavar="TREE_NUMBER")
    parser.add_argument("-o", metavar="OUT_DIR", default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()

    if args.build_index:
        build_index()

    if args.mesh_synonyms:
        mesh_synonyms(args.mesh_synonyms, args.o)


if __name__ == "__main__":
    main()
