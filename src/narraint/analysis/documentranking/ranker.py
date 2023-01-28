from copy import copy
from typing import List

import nltk

from narraint.analysis.querytranslation.data_graph import Query, DataGraph
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.document.narrative_document import NarrativeDocument

stopwords = set(nltk.corpus.stopwords.words('english'))
trans_map = {p: ' ' for p in '[]()?!'}  # PUNCTUATION}
translator = str.maketrans(trans_map)


class AnalyzedQuery:

    def __init__(self, keyword_query):
        self.keyword_query_org = keyword_query
        keyword_query = keyword_query.lower().strip()
        keyword_query = keyword_query.translate(translator)
        possible_keywords = keyword_query.split(' ')
        self.keyword_query = keyword_query
        self.keywords = list([k for k in possible_keywords if k and k not in stopwords])
        self.concepts = set()
        self.tagger = EntityTaggerJCDL.instance()
        self.__greedy_find_concepts_in_keywords()

    def __greedy_find_concepts_in_keywords(self):
        for i in range(len(self.keywords), 0, -1):
            current_part = ' '.join([k for k in self.keywords[:i]])
            try:
                entities_in_part = self.tagger.tag_entity(current_part, expand_search_by_prefix=False)
                self.concepts.update(entities_in_part)
                # print(f'Found {entities_in_part} in query part: {current_part}')
                break
            except KeyError:
                # print(f'No match for query part: {current_part}')
                pass


def retrieve_document_ids_for_query(query: AnalyzedQuery, data_graph: DataGraph):
    q = Query()
    for k in query.keywords:
        q.add_term(k)
    return data_graph.compute_query(q)


class AnalyzedNarrativeDocument:

    def __init__(self, doc: NarrativeDocument):
        self.document = doc
        self.concept_ids = set([t.ent_id for t in doc.tags])
        self.subject_ids = set([s.subject_id for s in doc.extracted_statements])
        self.object_ids = set([s.object_id for s in doc.extracted_statements])
        self.statement_concepts = set([(s.subject_id, s.object_id) for s in doc.extracted_statements])
        

class AbstractDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass


class TagOverlapDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            doc_scores.append((d.document.id, len(query.concepts.intersection(d.concept_ids))))

        return sorted([d for d in doc_scores], key=lambda x: x[1], reverse=True)


class ConceptStatementPartialOverlapDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            score = len(query.concepts.intersection(d.subject_ids)) + len(query.concepts.intersection(d.object_ids))
            doc_scores.append((d.document.id, score))

        return sorted([d for d in doc_scores], key=lambda x: x[1], reverse=True)


class ConceptStatementOverlapDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            score = 0
            for s in query.concepts:
                for o in query.concepts:
                    if (s, o) in d.statement_concepts:
                        score += 1
            doc_scores.append((d.document.id, score))

        return sorted([d for d in doc_scores], key=lambda x: x[1], reverse=True)


class GraphConnectivityDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass
