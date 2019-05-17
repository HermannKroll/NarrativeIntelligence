mkdir data

wget http://ctdbase.org/reports/CTD_chem_gene_ixns.tsv.gz 
mv CTD_chem_gene_ixns.tsv.gz data/CTD_chem_gene_ixns.tsv.gz
wget http://ctdbase.org/reports/CTD_chemicals_diseases.tsv.gz 
mv CTD_chemicals_diseases.tsv.gz data/CTD_chemicals_diseases.tsv.gz
wget http://ctdbase.org/reports/CTD_genes_diseases.tsv.gz 
mv CTD_genes_diseases.tsv.gz  data/CTD_genes_diseases.tsv.gz
wget ftp://nlmpubs.nlm.nih.gov/online/mesh/MESH_FILES/xmlmesh/desc2019.xml
mv desc2019.xml data/desc2019.xml