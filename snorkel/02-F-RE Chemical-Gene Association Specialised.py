#!/usr/bin/env python
# coding: utf-8

# Reload Snorkel Session

# In[ ]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')
get_ipython().run_line_magic('matplotlib', 'inline')

from snorkel import SnorkelSession

session = SnorkelSession()


# Load Train, Dev and Test sentences. Default Split is 1:1:1

# In[ ]:


from snorkel.ksnorkel import KSUtils

train_sent, dev_sent, test_sent = KSUtils.split_sentences(session, split=[0.8, 0.1, 0.1], seed=12345)


# In[ ]:


sent1 = train_sent[25]

print(sent1)

for i, w in enumerate(sent1.words):
    print('Word: {}\tPos: {}\tET: {}'.format(w, sent1.pos_tags[i], sent1.entity_types[i]))
    #print(sent1.dep_labels[i])
    print(sent1.lemmas[i])
    print(sent1.dep_parents[i])


# Now generate all candidates for each sentence set

# In[ ]:


from snorkel.models import candidate_subclass
from snorkel.candidates import PretaggedCandidateExtractor

ChemicalGeneInteraction = candidate_subclass('ChemicalGeneInteraction', ['chemical', 'gene'])
candidate_extractor = PretaggedCandidateExtractor(ChemicalGeneInteraction, ['Chemical', 'Gene'])

for k, sents in enumerate([train_sent,dev_sent, test_sent]):  
    candidate_extractor.apply(sents, split=k, clear=True)
    print("Number of candidates:", session.query(ChemicalGeneInteraction).filter(ChemicalGeneInteraction.split == k).count())


# Load CTD Dataset as gold label for drug disease associations
# (see http://ctdbase.org/downloads/)

# In[ ]:


import gzip

ctd_chem_gene_inter = set()
i = 0

statistics = {}
ctd_chem_gene_per_type = {}

with gzip.open('data/CTD_chem_gene_ixns.tsv.gz','r') as f:
    for l in f:
        line = str(l).replace('b\'', '').replace('\\n\'', '').replace('\\r','')
        # skip comments
        if line.startswith('#'):
            continue
        #print(line)
        components = line.split('\\t')    
        
        # add MESH:
        if not components[1].startswith('MESH:'):
            components[1] = "MESH:" + components[1]
            
        
            
        chemical = components[1]
        gene = components[4]
        key = frozenset((chemical, gene))
        ctd_chem_gene_inter.add(key)
        
        interaction_types = components[9].split('|')
        for i_t in interaction_types:
            if i_t not in statistics:
                statistics[i_t] = 1
                ctd_chem_gene_per_type[i_t] = set(key)
                continue
            statistics[i_t] += 1
            ctd_chem_gene_per_type[i_t].add(key)
        
        i += 1

    
print('{} chemical-gene assocations read from ChG-CTD_chem_gene_ixns'.format(len(ctd_chem_gene_inter)))


# In[ ]:


def cand_in_chemical_gene_interactions(c):
    key = frozenset((c.chemical_cid, c.gene_cid))
    if key in ctd_chem_gene_inter:
        return 1
    return -1

def cand_in_chemical_gene_by_interaction_type(c, interaction_type):
    key = frozenset((c.chemical_cid, c.gene_cid))
    if key in ctd_chem_gene_per_type[interaction_type]:
        return 1
    return -1 


# In[ ]:


import operator 

statistics_sorted = sorted(statistics.items(), key=operator.itemgetter(1), reverse=False)

interaction_types_to_extract = []
for k,v in statistics_sorted:
    print('{}: {}'.format(k,v))
    
    if v > 1000:
        interaction_types_to_extract.append(k)


# In[ ]:


print('Will check the following interaction types... {}'.format(interaction_types_to_extract))


# In[ ]:


from snorkel.ksnorkel import KSUtils
from snorkel.annotations import LabelAnnotator
from snorkel.learning import GenerativeModel
from snorkel.annotations import load_gold_labels
from snorkel.pytorch_gpu import LSTM
import torch

trained_interactions_lstms = []
skipped_interactions = []
    
# Go through all interaction types
for inter_type in interaction_types_to_extract:
    print('='*60) 
    print('='*60)
    inter_type_human_readable = inter_type.replace('^', '_')
    print('Starting with interaction type: {}'.format(inter_type))
    print('='*60)
    # compute gold label function regarding the interaction type
    lookup_dict = ctd_chem_gene_per_type[inter_type]
    def gold_label_function(c):
        key = frozenset((c.chemical_cid, c.gene_cid))
        if key in lookup_dict:
            return 1
        return -1 
    # add all gold label candidates
    pos_train_labels,_,_,_ = KSUtils.add_gold_labels_for_candidates(session, ChemicalGeneInteraction, gold_label_function)
    
    if pos_train_labels < 100:
        print('Skipping interaction_type: {} (only {} pos train candidates)'.format(inter_type_human_readable, pos_train_labels))
        skipped_interactions.append(inter_type_human_readable)
        continue
    
    # labeling function regarding ctd lookup
    def LF_cg_in_CTD(c):
        if gold_label_function(c) == 1:
            return 1
        return -1
    LFs = [ LF_cg_in_CTD ]

    # Label all candidates
    labeler = LabelAnnotator(lfs=LFs)
    get_ipython().run_line_magic('time', 'L_train = labeler.apply(split=0)')
    L_train
    
    # label dev and test aswell
    L_dev = labeler.apply_existing(split=1)
    L_test = labeler.apply_existing(split=2)
   
    # load gold labels
    L_gold_dev = load_gold_labels(session, annotator_name='gold',split=1)
    L_gold_test = load_gold_labels(session, annotator_name='gold', split=2)
   

    # train generative model
    gen_model = GenerativeModel()
    gen_model.train(L_train, epochs=100, decay=0.95, step_size=0.1 / L_train.shape[0], reg_param=1e-6)
    train_marginals = gen_model.marginals(L_train)
    
    # get all candidates from db
    all_cands, train_cands, dev_cands, test_cands = KSUtils.get_all_candidates(session, ChemicalGeneInteraction)
    

    # Best Configuration after grid search
    train_kwargs = {
        'batchsize':       64,
        'lr':              0.001,
        'embedding_dim':   100,
        'hidden_dim':      150,
        'n_epochs':        100,
        'dropout':         0.25,
        'rebalance':       0.0,
        'seed':            1701,
        'print_freq':        25,
        'cudnn_device':    'cuda:1'
    }
    
    # train LSTM
    lstm = LSTM(n_threads=10)
    lstm.train(train_cands, train_marginals, X_dev=dev_cands, Y_dev=L_gold_dev,use_cudnn=True, **train_kwargs)
    
    # evaluate LSTM
    tp, fp, tn, fn = lstm.error_analysis(session, test_cands, L_gold_test)
    
    lstm_path = 'chemical_gene_interaction_{}.lstm'.format(inter_type_human_readable)
    lstm.save(lstm_path)
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    trained_interactions_lstms.append(inter_type_human_readable)
print('='*60) 
print('='*60)
print('Finished')
print('='*60) 
print('='*60)
print('Trained LSTMs: {}'.format(trained_interactions_lstms))
print('Skipped Trainings: {}'.format(skipped_interactions))


# In[ ]:


session.rollback()
session.commit()

