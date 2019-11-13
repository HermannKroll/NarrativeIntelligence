import operator
from library_graph import LibraryGraph
from mesh.data import MeSHDB
from story import MeshTagger
from story import GeneTagger
from story import StoryProcessor

lg = LibraryGraph()
lg.read_from_tsv('../data/lg_pmc_sim_ami_108.tsv')


#sorted_preds = sorted(lg.predicate2enttypes.items(), key=operator.itemgetter(0))
#for key, types in sorted_preds:
#    print('<p>{} : {}</p>'.format(key, types))

db = MeSHDB.instance()
db.load_xml('../data/desc2020.xml')

story = StoryProcessor(lg, [MeshTagger(db)]) #, GeneTagger('../data/CTD_genes.tsv.gz')])

q1 = 'Simvastatin "1576" Amiodarone Rhabdomyolysis associated'
q2 = 'Simvastatin (1576) Amiodarone inhibits metabolites'
q3 = 'Simvastatin Rhabdomyolysis Amiodarone associated'
q4 = 'Simvastatin Hyperlipidemias Amiodarone "Diabetes Mellitus" therapeutic'



cq = q1
#results = story.query(cq)
print(story.tag_entities_in_keywords_human_readable(cq))

#for r in results:
#    print('Query: {}'.format(r[0]))
#    print('Docs: {}'.format(r[1]))
#    print('='*60)
