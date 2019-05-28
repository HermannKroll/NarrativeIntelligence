from library_graph import LibraryGraph
from story import MeshTagger
from story import StoryProcessor
from mesh.data import MeSHDB


lg = LibraryGraph()
lg.read_from_tsv('../data/lg_pmc_sim_ami_108.tsv')

db = MeSHDB().instance()
db.load_xml('../data/desc2019.xml')

story = StoryProcessor(lg, [MeshTagger(db)])

results = story.query('Simvastatin Rhabdomyolysis associated')

for r in results:
    print('Query: {}'.format(r[0]))
    print('Docs: {}'.format(r[1]))
    print('='*60)