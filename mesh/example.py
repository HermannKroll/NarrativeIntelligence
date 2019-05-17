"""
This is an example file how to use the package.
"""
from mesh.data import MeSHDB

db = MeSHDB.instance()

# Load XML file
db.load_xml("data/desc2019.xml")

# Select descriptor by Unique ID
desc01 = db.desc_by_id("D000001")

# Select descriptor by Tree Number
desc02 = db.desc_by_tree_number("D03.633.100.759.160")

# Print details found in XML file
desc01.print()

# Print all details (even those which are not contained in the XML file)
desc01.print(print_unset=True)

# Show all the available attributes of an descriptor
print(desc01.attrs)

# Get parent descriptor
parent_of_01 = desc01.parent

# Get the lineage of a descriptor
lineage_of_01 = desc01.lineage

# Get the common lineage of descriptor 01 and descriptor 02
common_lineage = desc01.get_common_lineage(desc02)

# Search descriptors by name (provided name must be contained in MeSH heading)
desc_list_allo = db.descs_by_name("Allo")

# Get descriptors by one of their entry terms / synonyms
desc_rimapurinol = db.descs_by_name("Rimapurinol")
# Alternative:
# desc_rimapurinol = db.descs_by_term("Rimapurinol")
