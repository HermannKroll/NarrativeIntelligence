import random

from snorkel import SnorkelSession
from snorkel.models import Document, Sentence
from snorkel.models.candidate import Marginal
from snorkel.lf_helpers import get_tagged_text

def split_sentences(session, split = [0.8, 0.1, 0.1], seed = 12345):
	if len(split) != 3:
		print('Error: split must consist of 3 values')
		return None
	
	sum_split = split[0] + split[1] + split[2]
	if  sum_split > 1.001 or sum_split < 0.9999:
		print('Error: sum of split prob. must be 1. It is {}'.format(sum_split))
		return None

	print('Splitting with probabilities {} and seed {}'.format(split, seed))

	docs = session.query(Document)
	train_sent, dev_sent, test_sent = [],[],[]

	amount_of_docs = session.query(Document).count()
	print("Amount of docs: {}".format(amount_of_docs))

	train_ids, dev_ids, test_ids = set(), set(), set()
	# compute thresholds
	t1 = split[0]
	t2 = split[0] + split[1]

	# use seed for random
	random.seed(seed)
	for i in range(0, amount_of_docs):
		rand = random.random() # get a random number between 0.0 and 1.0

		if rand < t1:
			train_ids.add(i)
		elif rand < t2:
			dev_ids.add(i)
		else:
			test_ids.add(i)

	print("Document splitted: {} train, {} dev and {} test".format(len(train_ids), len(dev_ids), len(test_ids)))


	for i, doc in enumerate(docs):
		for s in doc.sentences:
			if i in train_ids:
				train_sent.append(s)
			if i in dev_ids:
				dev_sent.append(s)
			if i in test_ids:
				test_sent.append(s)

	print("Sentences splitted: {} train, {} dev and {} test".format(len(train_sent), len(dev_sent), len(test_sent)))
	return train_sent, dev_sent, test_sent
	

from snorkel.models import GoldLabel, GoldLabelKey
from snorkel.lf_helpers import get_tagged_text



def add_gold_label_for_cand(session, c, label_function):
	cand_label_value = label_function(c)
	cand_id = c.id
	 
	query = session.query(GoldLabel).filter(GoldLabel.candidate_id == cand_id)
	if query.count() == 0:
		session.add(GoldLabel(
			key_id=0,
			candidate_id=cand_id,
			value=cand_label_value))
		
	return cand_label_value

def add_gold_labels_for_candidates(session, candidate_type, label_function, clear=True):
	if clear:
		print('Clearing existing gold labels...')
		# delete all gold label
		session.query(GoldLabel).delete()


	train_cands = session.query(candidate_type).filter(candidate_type.split == 0).all()
	dev_cands = session.query(candidate_type).filter(candidate_type.split == 1).all()
	test_cands = session.query(candidate_type).filter(candidate_type.split == 2).all()

	# add gold label key
	q_glk = session.query(GoldLabelKey).filter(GoldLabelKey.id == 0)
	if q_glk.count() == 0:
		session.add(GoldLabelKey(id = 0, name='gold', group=0))


	print("Adding gold labels to training candidates...")
	pos_labels = 0
	neg_labels = 0
	for c in train_cands:
		if add_gold_label_for_cand(session, c, label_function) == 1:
			pos_labels += 1
		else:
			neg_labels += 1


	print("Labeld {} positive and {} negative samples in train".format(pos_labels, neg_labels))
	pos_labels_sum = pos_labels
	neg_labels_sum = neg_labels
	pos_labels = 0
	neg_labels = 0
	print("Adding gold labels to develop candidates...")
	for c in dev_cands:
		if add_gold_label_for_cand(session, c, label_function) == 1:
			pos_labels += 1
		else:
			neg_labels += 1


	print("Labeld {} positive and {} negative samples in dev".format(pos_labels, neg_labels))
	pos_labels_sum += pos_labels
	neg_labels_sum += neg_labels
	pos_labels = 0
	neg_labels = 0
	print("Adding gold labels to test candidates...")
	for c in test_cands:
		if add_gold_label_for_cand(session, c, label_function) == 1:
			pos_labels += 1
		else:
			neg_labels += 1

			
	print("Labeld {} positive and {} negative samples in test".format(pos_labels, neg_labels))
	pos_labels_sum += pos_labels
	neg_labels_sum += neg_labels
	print("Finished - commiting to database...")
	# Commit session
	session.commit()
	print("Commit complete!")

	train_cands = None
	dev_cands = None
	test_cands = None

	print("Labeld {} positive and {} negative samples".format(pos_labels_sum, neg_labels_sum))



def save_binary_relation_confusion_matrix_as_tsv(filename, session, all_cands, all_sents, header_str, cand_cid_a_name, cand_cid_b_name, prob_threshold=0.5):
	print("Storing candidate labels into result file: {}".format(filename))
	amount_of_candidates = len(all_cands)
	print("Amount of candidates: {}".format(amount_of_candidates))

	print('Load mariginals from db...')
	marginals = session.query(Marginal).all()

	cand_probability = {}
	for marg in marginals:
		cand_probability[marg.candidate_id] = marg.probability
	print('Marginals loaded!')


	print('Load gold labels from db...')
	gold_labels = session.query(GoldLabel).all()

	cand_gold_label = {}
	for gl in gold_labels:
		cand_gold_label[gl.candidate_id] = gl.value
	print('Gold labels loaded!')

	amount_of_true_predicitions = 0

	f_fp = open(filename.replace('.tsv', '_FP.tsv'), 'w')
	f_tp = open(filename.replace('.tsv', '_TP.tsv'), 'w')
	f_tn = open(filename.replace('.tsv', '_TN.tsv'), 'w')
	f_fn = open(filename.replace('.tsv', '_FN.tsv'), 'w')

	f_fp.write(header_str)
	f_tp.write(header_str)
	f_tn.write(header_str)
	f_fn.write(header_str)
	
	i_fp = 0
	i_tp = 0
	i_tn = 0
	i_fn = 0

	print('Start writing files...')
	# iterate over all candidates
	for cand in all_cands:
		prob = cand_probability[cand.id]
		gold_label = cand_gold_label[cand.id]

		f = None
		# TP
		if prob >= prob_threshold and gold_label == 1:  
			f = f_tp
			i_tp += 1
		# FP
		elif prob >= prob_threshold and gold_label == -1:
			f = f_fp
			i_fp += 1
		# FN
		elif prob < prob_threshold and gold_label == 1:
			f = f_fn
			i_fn += 1
		# TN
		elif prob < prob_threshold and gold_label == -1:
			f = f_tn
			i_tn += 1


		contexts = cand.get_contexts()

		a_cid = getattr(cand, cand_cid_a_name)
		b_cid = getattr(cand, cand_cid_b_name)
		a_context = contexts[0]
		b_context = contexts[1]
		a_span = a_context.get_span()
		b_span = b_context.get_span()

		# we assume both spans to be in the same document
		sent_id = a_context.sentence_id
		# extract the sentence
		sentence = get_tagged_text(cand)

		result_str = '\n{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(sent_id, cand.id, a_cid, a_span, b_cid, b_span, sentence)
		f.write(result_str)
		

	f_tp.close()
	f_fp.close()
	f_fn.close()
	f_tn.close()
	print("Saved {} TP, {} FP, {} TN, {} FN facts in files.".format(i_tp, i_fp, i_tn, i_fn))



def save_binary_relation_as_tsv(filename, session, all_cands, all_sents, header_str, cand_cid_a_name, cand_cid_b_name, prob_threshold=0.5):
	print("Storing candidate labels into result file: {}".format(filename))
	amount_of_candidates = len(all_cands)
	print("Amount of candidates: {}".format(amount_of_candidates))

	print('Load mariginals from db...')
	marginals = session.query(Marginal).all()

	cand_probability = {}
	for marg in marginals:
		cand_probability[marg.candidate_id] = marg.probability
	print('Marginals loaded!')

	print('Building sentence to document map...')
	sent_id_to_doc = {}
	for sent in all_sents:
		sent_id_to_doc[sent.id] = sent.document_id
	print('Map built!')

	amount_of_true_predicitions = 0
	with open(filename, 'w') as f:
		f.write(header_str)
		for cand in all_cands:
			prob = cand_probability[cand.id]
			if prob >= prob_threshold:  
				contexts = cand.get_contexts()

				a_cid = getattr(cand, cand_cid_a_name)
				b_cid = getattr(cand, cand_cid_b_name)
				a_context = contexts[0]
				b_context = contexts[1]
				a_span = a_context.get_span()
				b_span = b_context.get_span()

				# we assume both spans to be in the same document
				sent_id = a_context.sentence_id
				doc_id = sent_id_to_doc[sent_id]

				result_str = '\n{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(doc_id, sent_id, cand.id, a_cid, a_span, b_cid, b_span)
				#print(result_str)
				f.write(result_str)
				
				amount_of_true_predicitions += 1

	print("Saved {} positive predicitions for binary relation!".format(amount_of_true_predicitions))
