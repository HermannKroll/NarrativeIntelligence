from narraint.backend.database import SessionExtended
from narraint.backend.models import TagInvertedIndex
from narraint.recommender.core import NarrativeCoreExtractor, NarrativeConceptCore
from narraint.recommender.document import RecommenderDocument
from narraint.recommender.recommender_config import FS_DOCUMENT_CUTOFF, FS_DOCUMENT_CUTOFF_HARD


class FirstStage:
    """
    Previously called FSConceptFlex, now default first stage implementation.
    """

    def __init__(self, extractor: NarrativeCoreExtractor):
        self.extractor = extractor
        self.document_collections = None
        self.session = SessionExtended.get()

    def retrieve_documents_for(self, document: RecommenderDocument, document_collections: [str]):
        self.document_collections = list(document_collections)
        # Compute the cores
        core = self.extractor.extract_concept_core(document)

        # We dont have any core
        if not core:
            return []

        # score documents with this core
        document_ids_scored = self.score_document_ids_with_core(core)

        # We did not find any documents
        if len(document_ids_scored) == 0:
            return []

        # Ensure cutoff
        return self.apply_dynamic_cutoff(document_ids_scored)

    def retrieve_documents(self, concept: str, concept_type: str):
        q = self.session.query(TagInvertedIndex)
        # Search for matching nodes but not for predicates (ignore direction)
        q = q.filter(TagInvertedIndex.entity_id == concept)
        q = q.filter(TagInvertedIndex.entity_type == concept_type)
        if len(self.document_collections) == 1:
            q = q.filter(TagInvertedIndex.document_collection == self.document_collections[0])
        else:
            q = q.filter(TagInvertedIndex.document_collection.in_(self.document_collections))
        document_ids = set()
        for row in q:
            document_ids.update(TagInvertedIndex.prepare_document_ids(row.document_ids))

        return document_ids

    def score_document_ids_with_core(self, core: NarrativeConceptCore):
        import datetime
        start = datetime.datetime.now()
        # Core statements are also sorted by their score
        document_ids_scored = {}
        # If a statement of the core is contained within a document, we increase the score
        # of the document by the score of the corresponding edge
        for idx, concept in enumerate(core.concepts):
            # retrieve matching documents
            document_ids = self.retrieve_documents(concept.concept, concept.concept_type)

            for doc_id in document_ids:
                if doc_id not in document_ids_scored:
                    document_ids_scored[doc_id] = concept.score
                else:
                    document_ids_scored[doc_id] += concept.score
        print("score_document_ids_with_core took ", datetime.datetime.now() - start)
        return self.normalize_and_sort_document_scores(document_ids_scored)

    @staticmethod
    def normalize_and_sort_document_scores(document_ids_scored):
        # We did not find any documents
        if len(document_ids_scored) == 0:
            return []

        # Get the maximum score to normalize the scores
        max_score = max(document_ids_scored.values())
        if max_score > 0.0:
            # Convert to list
            document_ids_scored = [(k, v / max_score) for k, v in document_ids_scored.items()]
        else:
            document_ids_scored = [(k, v) for k, v in document_ids_scored.items()]
        # Sort by score and then doc desc
        document_ids_scored.sort(key=lambda x: (x[1], int(x[0])), reverse=True)
        return document_ids_scored

    @staticmethod
    def apply_dynamic_cutoff(document_ids_scored):
        if len(document_ids_scored) > FS_DOCUMENT_CUTOFF:
            # get score at position
            score_at_cutoff = document_ids_scored[FS_DOCUMENT_CUTOFF][1]
            # search position where score is lower
            new_cutoff_position = 0
            for idx, (d, score) in enumerate(document_ids_scored[FS_DOCUMENT_CUTOFF:]):
                if score < score_at_cutoff:
                    new_cutoff_position = idx
                    break
            if FS_DOCUMENT_CUTOFF + new_cutoff_position < FS_DOCUMENT_CUTOFF_HARD:
                return document_ids_scored[:FS_DOCUMENT_CUTOFF + new_cutoff_position]
            else:
                return document_ids_scored[:FS_DOCUMENT_CUTOFF_HARD]
        else:
            # Ensure cutoff
            return document_ids_scored[:FS_DOCUMENT_CUTOFF]
