import argparse
import pickle

from frontend.frontend.settings import base as settings
from mesh.data import MeSHDB


def build_index():
    db = MeSHDB.instance()
    db.load_xml(settings.DESCRIPTOR_FILE, True, True)
    with open(settings.MESHDB_INDEX, "wb") as f:
        pickle.dump(db.get_index(), f)


def mesh_synonyms(tree_number_list, output):
    db = MeSHDB.instance()
    db.load_xml(settings.DESCRIPTOR_FILE, verbose=True)

    descs = set()
    for tree_number in tree_number_list:
        print("Querying descriptors for {}".format(tree_number))
        descs |= set(db.descs_under_tree_number(tree_number))
        descs.add(db.desc_by_tree_number(tree_number))
    print("Found {} descriptors".format(len(descs)))

    print("Collecting data ...")
    data = sorted((desc.unique_id, desc.heading, ", ".join(t.string for t in desc.terms)) for desc in descs)

    with open(output, "w") as f:
        for line in data:
            f.write("MESH:{}\t{}\t{}\n".format(*line))
    print("Done.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--mesh-synonyms", nargs="+", metavar="TREE_NUMBER")
    parser.add_argument("-o", metavar="OUT")
    args = parser.parse_args()

    if args.build_index:
        build_index()

    if args.mesh_synonyms:
        mesh_synonyms(args.mesh_synonyms, args.o)


if __name__ == "__main__":
    main()
