"""
This is an example file how to use the package.
"""
from narraint.config import MESH_DESCRIPTORS_FILE
from narraint.mesh.data import MeSHDB

db = MeSHDB.instance()

# Load XML file
db.load_xml(MESH_DESCRIPTORS_FILE)

# Select descriptor by Unique ID
desc01 = db.desc_by_id("D000001")

# Select descriptor by Tree Number
desc02 = db.desc_by_tree_number("D03.633.100.759.160")

# Get all children of a descriptor with a tree number
children = db.descs_under_tree_number("D03.633.100.759.160")

# Print details found in XML file
desc01.print()

# Print all details (even those which are not contained in the XML file)
desc01.print(print_unset=True)

# Show all the available attributes of an descriptor
print(desc01.attrs)

# Get parents of descriptor
parents_of_01 = desc01.parents

# Get the lineages of a descriptor
lineages_of_01 = desc01.lineages

# Get the common lineages of descriptor 01 and descriptor 02
common_lineages = desc01.get_common_lineage(desc02)

# Search descriptors by name (provided name must be contained in MeSH heading)
desc_list_allo = db.descs_by_name("Allo")

# Get descriptors by one of their entry terms / synonyms
desc_rimapurinol = db.descs_by_name("Rimapurinol")
# Alternative:
# desc_rimapurinol = db.descs_by_term("Rimapurinol")
