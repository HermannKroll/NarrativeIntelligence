from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *
from future.utils import iteritems

from collections import defaultdict
from copy import deepcopy
from itertools import product
import re
from sqlalchemy.sql import select

from snorkel.models import Candidate, TemporarySpan, Sentence
from snorkel.udf import UDF, UDFRunner


class FilteredPretaggedCandidateExtractor(UDFRunner):
	"""UDFRunner for PretaggedCandidateExtractorUDF"""
	def __init__(self, candidate_class, entity_types, regex_to_search, self_relations=False, nested_relations=False, symmetric_relations=True, entity_sep='~@~'):
		super(FilteredPretaggedCandidateExtractor, self).__init__(
			FilteredPretaggedCandidateExtractorUDF, candidate_class=candidate_class,
			entity_types=entity_types, regex_to_search=regex_to_search, self_relations=self_relations,
			nested_relations=nested_relations, entity_sep=entity_sep,
			symmetric_relations=symmetric_relations,
		)

	def apply(self, xs, split=0, **kwargs):
		super(FilteredPretaggedCandidateExtractor, self).apply(xs, split=split, **kwargs)

	def clear(self, session, split, **kwargs):
		session.query(Candidate).filter(Candidate.split == split).delete()


class FilteredPretaggedCandidateExtractorUDF(UDF):		

	"""
	Extension: Filters sentences for specific keywords
	"""
	def __init__(self, candidate_class, entity_types, regex_to_search, self_relations=False, nested_relations=False, symmetric_relations=False, entity_sep='~@~', **kwargs):
		self.candidate_class     = candidate_class
		self.entity_types        = entity_types
		self.regex_to_search 	 = regex_to_search
		self.arity               = len(entity_types)
		self.self_relations      = self_relations
		self.nested_relations    = nested_relations
		self.symmetric_relations = symmetric_relations
		self.entity_sep          = entity_sep

		super(FilteredPretaggedCandidateExtractorUDF, self).__init__(**kwargs)

	def apply(self, context, clear, split, check_for_existing=True, **kwargs):
		"""Extract Candidates from a Context"""
		# For now, just handle Sentences
		if not isinstance(context, Sentence):
			raise NotImplementedError("%s is currently only implemented for Sentence contexts." % self.__name__)

		if not self.regex_to_search:
			raise NotImplementedError('Regex cannot be empty: {}'.format(self.__name__))

		sentence_str = context.text
		# First search for regex in sentence
		if not re.search(self.regex_to_search, sentence_str):
			return  # Sentence does not fullfill our regex

		# Do a first pass to collect all mentions by entity type / cid
		entity_idxs = dict((et, defaultdict(list)) for et in set(self.entity_types))
		L = len(context.words)
		for i in range(L):
			if context.entity_types[i] is not None:
				ets  = context.entity_types[i].split(self.entity_sep)
				cids = context.entity_cids[i].split(self.entity_sep)
				for et, cid in zip(ets, cids):
					if et in entity_idxs:
						entity_idxs[et][cid].append(i)

		# Form entity Spans
		entity_spans = defaultdict(list)
		entity_cids  = {}
		for et, cid_idxs in iteritems(entity_idxs):
			for cid, idxs in iteritems(entity_idxs[et]):
				while len(idxs) > 0:
					i          = idxs.pop(0)
					char_start = context.char_offsets[i]
					char_end   = char_start + len(context.words[i]) - 1
					while len(idxs) > 0 and idxs[0] == i + 1:
						i        = idxs.pop(0)
						char_end = context.char_offsets[i] + len(context.words[i]) - 1

					# Insert / load temporary span, also store map to entity CID
					tc = TemporarySpan(char_start=char_start, char_end=char_end, sentence=context)
					tc.load_id_or_insert(self.session)
					entity_cids[tc.id] = cid
					entity_spans[et].append(tc)

		# Generates and persists candidates
		candidate_args = {'split' : split}
		for args in product(*[enumerate(entity_spans[et]) for et in self.entity_types]):
		
			# TODO: Make this work for higher-order relations
			if self.arity == 2:
				ai, a = args[0]
				bi, b = args[1]

				# Check for self-joins, "nested" joins (joins from span to its subspan), and flipped duplicate
				# "symmetric" relations
				if not self.self_relations and a == b:
					continue
				elif not self.nested_relations and (a in b or b in a):
					continue
				elif not self.symmetric_relations and ai > bi:
					continue

			# Assemble candidate arguments
			for i, arg_name in enumerate(self.candidate_class.__argnames__):
				candidate_args[arg_name + '_id'] = args[i][1].id
				candidate_args[arg_name + '_cid'] = entity_cids[args[i][1].id]

			# Checking for existence
			if check_for_existing:
				q = select([self.candidate_class.id])
				for key, value in iteritems(candidate_args):
					q = q.where(getattr(self.candidate_class, key) == value)
				candidate_id = self.session.execute(q).first()
				if candidate_id is not None:
					continue

			# Add Candidate to session
			yield self.candidate_class(**candidate_args)
