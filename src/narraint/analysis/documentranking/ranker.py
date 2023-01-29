from typing import List

import nltk

from narraint.analysis.querytranslation.data_graph import Query, DataGraph
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.backend.database import SessionExtended
from narraint.backend.retrieve import retrieve_narrative_documents_from_database
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
        for j in range(0, len(self.keywords), 1):
            keywords_iteration = self.keywords[j:]
            for i in range(len(keywords_iteration), 0, -1):
                current_part = ' '.join([k for k in keywords_iteration])
                try:
                    entities_in_part = self.tagger.tag_entity(current_part, expand_search_by_prefix=False)
                    self.concepts.update(entities_in_part)
                    # print(f'Found {entities_in_part} in query part: {current_part}')
                    break
                except KeyError:
                    # print(f'No match for query part: {current_part}')
                    pass


class AnalyzedNarrativeDocument:

    def __init__(self, doc: NarrativeDocument):
        self.document = doc
        self.concept_ids = set([t.ent_id for t in doc.tags])
        self.concept2frequency = {}
        for t in doc.tags:
            if t.ent_id not in self.concept2frequency:
                self.concept2frequency[t.ent_id] = 1
            else:
                self.concept2frequency[t.ent_id] += 1

        self.subject_ids = set([s.subject_id for s in doc.extracted_statements])
        self.object_ids = set([s.object_id for s in doc.extracted_statements])
        self.statement_concepts = set([(s.subject_id, s.object_id) for s in doc.extracted_statements])


class DocumentRetriever:

    def __init__(self):
        self.__cache = {}
        self.session = SessionExtended.get()

    def retrieve_narrative_documents(self, document_ids: [int], document_collection: str) -> List[
        AnalyzedNarrativeDocument]:
        if len(document_ids) == 0:
            return []

        document_ids = set(document_ids)
        found_ids = set()
        narrative_documents = []

        if document_collection not in self.__cache:
            self.__cache[document_collection] = {}

        # look which documents have been cached
        for did in document_ids:
            if did in self.__cache[document_collection]:
                found_ids.add(did)
                narrative_documents.append(self.__cache[did])

        remaining_document_ids = document_ids - found_ids
        if len(remaining_document_ids) == 0:
            return []
        narrative_documents_queried = retrieve_narrative_documents_from_database(session=self.session,
                                                                                 document_ids=document_ids,
                                                                                 document_collection=document_collection)

        narrative_documents_queried = [AnalyzedNarrativeDocument(d) for d in narrative_documents_queried]

        # add to cache
        for d in narrative_documents_queried:
            self.__cache[document_collection][d.document.id] = d

        # add them to list
        narrative_documents.extend(narrative_documents_queried)
        return narrative_documents

    def retrieve_document_ids_for_query(self, query: AnalyzedQuery, data_graph: DataGraph):
        q = Query()
        for k in query.keywords:
            q.add_term(k)
        return data_graph.compute_query(q)


class AbstractDocumentRanker:

    def __init__(self, name):
        self.name = name

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass


class EqualDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="EqualDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        return list([d.document.id for d in narrative_documents])


class ConceptDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="ConceptDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            doc_scores.append((d.document.id, len(query.concepts.intersection(d.concept_ids))))

        return list([res[0] for res in sorted(doc_scores, key=lambda x: x[1], reverse=True)])


class ConceptFrequencyDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="ConceptFrequencyDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            concept_frequency = sum([d.concept2frequency[c] for c in query.concepts if c in d.concept2frequency])
            doc_scores.append((d.document.id, concept_frequency))

        return list([res[0] for res in sorted(doc_scores, key=lambda x: x[1], reverse=True)])


class StatementPartialOverlapDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="StatementPartialOverlapDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            score = len(query.concepts.intersection(d.subject_ids)) + len(query.concepts.intersection(d.object_ids))
            doc_scores.append((d.document.id, score))

        return list([res[0] for res in sorted(doc_scores, key=lambda x: x[1], reverse=True)])


class StatementOverlapDocumentRanker(AbstractDocumentRanker):

    def __init__(self):
        super().__init__(name="StatementOverlapDocumentRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        doc_scores = []
        for d in narrative_documents:
            score = 0
            for s in query.concepts:
                for o in query.concepts:
                    if (s, o) in d.statement_concepts:
                        score += 1
            doc_scores.append((d.document.id, score))

        return list([res[0] for res in sorted(doc_scores, key=lambda x: x[1], reverse=True)])


class GraphConnectivityDocumentRanker:

    def __init__(self):
        pass

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass
