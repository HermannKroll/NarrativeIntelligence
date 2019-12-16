mkdir data

wget http://ctdbase.org/reports/CTD_chem_gene_ixns.tsv.gz 
mv CTD_chem_gene_ixns.tsv.gz data/CTD_chem_gene_ixns.tsv.gz

wget http://ctdbase.org/reports/CTD_chemicals_diseases.tsv.gz 
mv CTD_chemicals_diseases.tsv.gz data/CTD_chemicals_diseases.tsv.gz

wget http://ctdbase.org/reports/CTD_genes_diseases.tsv.gz 
mv CTD_genes_diseases.tsv.gz  data/CTD_genes_diseases.tsv.gz

wget ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/xmlmesh/desc2020.gz
gzip -d desc2020.gz
mv desc2020 data/desc2020.xml

wget ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz
gzip -d PMC-ids.csv.gz
mv PMC-ids.csv data/PMC-ids.csv