#!/usr/bin/env python
# coding: utf-8
import sys
import os
from time import time

from snorkel import SnorkelSession
from snorkel.parser import CorpusParser, Spacy, StanfordCoreNLPServer
from snorkel.models import Document, Sentence
from snorkel.models import Candidate, candidate_subclass
from snorkel.candidates import PretaggedCandidateExtractor

from pubtator import PubTatorDocPreprocessor, PubTatorTagProcessor, PubTatorParser

from ksnorkel import KSUtils

from pytorch_gpu import LSTM


# In[2]
result_path = 'results/pmc_10000/'
file = 'data/pmc_simvastatin_8712_filtered.pubtator'
file_out = 'data/temp/pmc_simvastatin_8712_filtered.pubtator'
extract_documents_again = False

result_lg_file = result_path + 'lg.tsv'
already_processed_docs_file = result_path + 'processed_docs.txt'
already_skipped_doc_file = result_path + 'skipped_docs.txt'

import os

try:
    os.mkdir(result_path)
except OSError:
    print("Creation of the directory {} failed because it may exists".format(result_path))
else:
    print("Successfully created the directory %s " % result_path)

if extract_documents_again:
    print('extracting single documents...')
    i = 0
    with open(file, 'r') as f:
        line_buffer = []
        for l in f:
            line_buffer.append(l)
            # split file here
            if l == '\n':
                fo_name = '{}.{}'.format(file_out, i)
                with open(fo_name, 'w') as fo:
                    for lo in line_buffer:
                        fo.write(lo)
                # print('{} written'.format(fo_name))
                line_buffer = []
                i += 1
    print('extraction finished')

# In[3]:

gene_chemical_interaction_types = ['increases_acetylation', 'affects_abundance', 'increases_reduction',
                                   'increases_localization', 'decreases_abundance', 'affects_metabolic processing',
                                   'increases_oxidation', 'decreases_secretion', 'affects_activity',
                                   'increases_degradation', 'increases_transport', 'increases_uptake',
                                   'increases_metabolic processing', 'decreases_phosphorylation',
                                   'decreases_response to substance', 'affects_localization', 'increases_cleavage',
                                   'increases_response to substance', 'increases_abundance',
                                   'increases_chemical synthesis', 'affects_methylation',
                                   'affects_response to substance', 'increases_secretion',
                                   'decreases_methylation', 'affects_reaction', 'increases_phosphorylation',
                                   'decreases_activity', 'increases_activity', 'increases_reaction',
                                   'affects_binding', 'affects_expression', 'decreases_reaction',
                                   'affects_cotreatment', 'decreases_expression', 'increases_expression',
                                   'affects_transport']
chemical_disease_interaction_types = ['therapeutic', 'marker_mechanism']

session = SnorkelSession()


def compute_candidates(cand_str, cand_type_pair, cand_type_pair_lower):
    cand_type = candidate_subclass(cand_str, cand_type_pair_lower)
    candidate_extractor = PretaggedCandidateExtractor(cand_type, cand_type_pair)
    for k, sents in enumerate([all_sents]):
        candidate_extractor.apply(sents, split=k, clear=True)
        print("Number of candidates:", session.query(cand_type).filter(cand_type.split == k).count())

    return cand_type


def load_and_apply_lstm(lstm_path, cand_type):
    lstm = LSTM(n_threads=1, device='cpu')
    lstm.load(lstm_path)

    # print("Loading all candidates from db...")
    all_cands = session.query(cand_type).filter(cand_type.split == 0).order_by(cand_type.id).all()
    # print("{} candidates load from db!".format(len(all_cands)))

    if len(all_cands) == 0:
        return all_cands

    # print("Applying LSTM to candidates...")
    lstm.save_marginals(session, all_cands)
    # print("LSTM applied!")
    return all_cands


if os.path.isfile(already_processed_docs_file):
    print('Resume work (procssed documents)....')
    with open(already_processed_docs_file, 'r') as f:
        already_processed_doc_ids = eval(f.read())
else:
    print('Starting from beginning (procssed documents)...')
    already_processed_doc_ids = set()

if os.path.isfile(already_skipped_doc_file):
    print('Resume work (skipped documents)....')
    with open(already_skipped_doc_file, 'r') as f:
        already_skipped_doc_ids = eval(f.read())
else:
    print('Starting from beginning (skipped documents)...')
    already_skipped_doc_ids = set()

sys.stdout.flush()

failed_documents = 0
for i in range(0, 8712):
    # skip allready processed or skipped documents
    if i in already_processed_doc_ids or i in already_skipped_doc_ids:
        continue

    try:
        print('<<<<<<<<<<<<<<<<<< Process Document {}  >>>>>>>>>>>>>>'.format(i))

        start_ts = time()
        file_name = '{}.{}'.format(file_out, i)
        doc_preprocessor = PubTatorDocPreprocessor(file_name, annotations=False, debug=True)
        parser = PubTatorParser(stop_on_err=False, debug=False)
        corpus_parser = CorpusParser(parser=parser)
        corpus_parser.apply(doc_preprocessor, parallelism=1, clear=True)
        end_ts = time()

        print("\nDONE in {}".format((time() - start_ts)))

        all_docs = session.query(Document).all()
        snorkel_to_real_doc_name = {}

        for doc in all_docs:
            snorkel_to_real_doc_name[doc.id] = doc.name

        # print("Loading all sentences from db...")
        all_sents = session.query(Sentence).all()
        # print("Loading complete!")
        session.expunge_all()

        # print('Amount of sentences: {}'.format(len(all_sents)))

        # print('Building sentence to document map...')
        sent_id_to_doc = {}
        for sent in all_sents:
            if sent.id not in sent_id_to_doc:
                sent_id_to_doc[sent.id] = snorkel_to_real_doc_name[sent.document_id]
        # print('Map built!')

        ChemicalDisease = compute_candidates('ChemicalDisease', ['Chemical', 'Disease'], ['chemical', 'disease'])
        all_cands = load_and_apply_lstm('chemical_disease.lstm', ChemicalDisease)
        KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc, 'chemical_cid',
                                       'Chemical', 'associated', 'disease_cid', 'Disease')

        session = SnorkelSession()

        ChemicalGeneInteraction = compute_candidates('ChemicalGeneInteraction', ['Chemical', 'Gene'],
                                                     ['chemical', 'gene'])
        all_cands = load_and_apply_lstm('chemical_gene_interaction.lstm', ChemicalGeneInteraction)
        KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc, 'chemical_cid',
                                       'Chemical', 'associated', 'gene_cid', 'Gene')

        session = SnorkelSession()

        GeneDiseaseInteraction = compute_candidates('GeneDiseaseInteraction', ['Gene', 'Disease'], ['gene', 'disease'])
        all_cands = load_and_apply_lstm('gene_disease_interaction.lstm', GeneDiseaseInteraction)
        KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc, 'gene_cid',
                                       'Gene', 'associated', 'disease_cid', 'Disease')

        session = SnorkelSession()

        GeneChemicalMetabolism = compute_candidates('GeneChemicalMetabolism', ['Gene', 'Chemical'],
                                                    ['gene', 'chemical'])
        all_cands = load_and_apply_lstm('gene_chemical_metabolism.lstm', GeneChemicalMetabolism)
        KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc, 'gene_cid',
                                       'Gene', 'metabolites', 'chemical_cid', 'Chemical')

        session = SnorkelSession()

        ChemicalGeneInhibition = compute_candidates('ChemicalGeneInhibition', ['Chemical', 'Gene'],
                                                    ['chemical', 'gene'])
        all_cands = load_and_apply_lstm('chemical_gene_inhibition.lstm', ChemicalGeneInhibition)
        KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc, 'chemical_cid',
                                       'Chemical', 'inhibits', 'gene_cid', 'Gene')

        session = SnorkelSession()

        # Tag candidates
        ChemicalGeneInteraction = compute_candidates('ChemicalGeneInteraction', ['Chemical', 'Gene'],
                                                     ['chemical', 'gene'])

        # go through all interactions
        print(len(gene_chemical_interaction_types))
        for inter_type in gene_chemical_interaction_types:
            inter_type = inter_type.replace(' ', '_')
            lstm_file = 'chemical_gene_interaction_{}.lstm'.format(inter_type)

            all_cands = load_and_apply_lstm(lstm_file, ChemicalGeneInteraction)

            KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc,
                                           'chemical_cid', 'Chemical', inter_type, 'gene_cid', 'Gene')
            session = SnorkelSession()
            print('=' * 60)

        ChemicalDisease = compute_candidates('ChemicalDisease', ['Chemical', 'Disease'], ['chemical', 'disease'])

        # go through all interactions
        print(len(chemical_disease_interaction_types))
        for inter_type in chemical_disease_interaction_types:
            inter_type = inter_type.replace(' ', '_')
            lstm_file = 'chemical_disease_interaction_{}.lstm'.format(inter_type)

            all_cands = load_and_apply_lstm(lstm_file, ChemicalDisease)

            KSUtils.append_relation_in_tsv(result_lg_file, session, all_cands, all_sents, sent_id_to_doc,
                                           'chemical_cid', 'Chemical', inter_type, 'disease_cid', 'Disease')
            session = SnorkelSession()
            print('=' * 60)

        print('=' * 60)
        print('=' * 60)
        print('=' * 60)

        already_processed_doc_ids.add(i)
        with open(already_processed_docs_file, 'w') as f:
            f.write(str(already_processed_doc_ids))

        sys.stdout.flush()

    except Exception as err:
        print('Error while processing {}: {}'.format(i, err))
        failed_documents += 1

        session.rollback()
        session.commit()

        already_skipped_doc_ids.add(i)
        with open(already_skipped_doc_file, 'w') as f:
            f.write(str(already_skipped_doc_ids))

        sys.stdout.flush()

        # print('Amount of docs: {}'.format(len(all_docs)))
        # with open(result_path + 'doc_mapping.tsv', 'w') as f:
        #    f.write('{}\t{}'.format('snorkel_id', 'pmid'))
        #    for doc in all_docs:
        #        f.write('\n{}\t{}'.format(doc.id, doc.name))
        # print('Finished')

