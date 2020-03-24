mkdir data

wget ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/xmlmesh/desc2020.gz
gzip -d desc2020.gz
mv desc2020 data/desc2020.xml

wget ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/xmlmesh/supp2020.gz
gzip -d supp2020.gz
mv supp2020 data/supp2020.xml

wget ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz
gzip -d PMC-ids.csv.gz
mv PMC-ids.csv data/PMC-ids.csv