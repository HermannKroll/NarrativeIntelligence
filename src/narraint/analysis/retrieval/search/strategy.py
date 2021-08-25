import math
import os
from itertools import product

from nltk.stem.porter import *

from narraint.analysis.retrieval.experiment_config import EXP_TEXTS_DIRECTORY
from narraint.extraction.versions import OPENIE_EXTRACTION, PATHIE_EXTRACTION
from narraint.frontend.ui.views import convert_query_text_to_fact_patterns
from narrant.entity.entity import Entity
from narrant.entity.entityresolver import EntityResolver
from narrant.entity.meshontology import MeSHOntology
from narrant.pubtator.document import TaggedDocument


def compute_f_measure(precision, recall):
    if precision + recall > 0.0:
        return 2 * (precision * recall) / (precision + recall)
    return 0.0


def calculate_prec_rec_f(doc_hits, ids_correct):
    doc_ids_correct = doc_hits.intersection(ids_correct)
    len_hits = len(doc_hits)
    len_correct = len(doc_ids_correct)
    if doc_ids_correct:
        precision = len_correct / len_hits
        recall = len_correct / len(ids_correct)
    else:
        precision = 0.0
        recall = 0.0
    return precision, recall, compute_f_measure(precision, recall)


class SearchStrategy:

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        pass


class TextSearchStrategy(SearchStrategy):

    def __init__(self, document_dir=EXP_TEXTS_DIRECTORY):
        self.document_dir = document_dir
        self.mesh_ontology = MeSHOntology.instance()
        self.entity_resolver = EntityResolver.instance()
        self.stemmer = PorterStemmer()

    def get_document_content(self, document_id: int, document_collection: str) -> TaggedDocument:
        doc_path = os.path.join(self.document_dir, '{}_{}.txt'.format(document_collection, document_id))
        with open(doc_path, 'r') as f:
            return TaggedDocument(f.read())

    def find_sentences_by_entity_id(self, entity: Entity, document: TaggedDocument):
        """
        Finds all sentence idxs which contain the entity id as a tag
        :param entity: the searched entity
        :param document: the current document
        :return: a set of sentence idxs
        """
        sentences = set()
        if entity.entity_type == 'MESH_ONTOLOGY':
            mesh_descs = self.mesh_ontology.find_descriptors_start_with_tree_no(entity.entity_id)
            for d in mesh_descs:
                desc_id = 'MESH:{}'.format(d[0])
                if desc_id in document.sentences_by_ent_id:
                    sentences.update(document.sentences_by_ent_id[desc_id])
        else:
            # TODO: Search by id, does not work with genes currently
            if entity.entity_id in document.sentences_by_ent_id:
                sentences.update(document.sentences_by_ent_id[entity.entity_id])
        return sentences

    def find_entity_positions(self, entity: Entity, document: TaggedDocument):
        meshs = entity.get_meshs()
        return {e.start for m in meshs if m in document.entities_by_ent_id for e in document.entities_by_ent_id.get(m)}

    def find_sentences_by_entity_name(self, entity: Entity, document: TaggedDocument):
        """
        Find all sentence ids which contain the entity name
        :param entity: the searched entity
        :param document: the current document
        :return: a set of sentence idxs
        """
        sentences = set()
        entity_name = self.entity_resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type,
                                                                   resolve_gene_by_id=False).lower().strip()
        if '//' in entity_name:
            entity_names = entity_name.split('//')
        else:
            entity_names = [entity_name]
        for entity_name in entity_names:
            for s_id, sent in document.sentence_by_id.items():
                s_lower = sent.text.lower().strip()
                if entity_name in s_lower:
                    sentences.add(s_id)
        return


class SentenceEntityCooccurrence(TextSearchStrategy):

    def __init__(self, document_dir=EXP_TEXTS_DIRECTORY):
        super().__init__(document_dir)
        self.name = "SentenceEntityCooccurrence"

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) -> (
            float, float, float):
        graph_query, _ = convert_query_text_to_fact_patterns(query)
        document_hits = set()
        for doc_id in ids_sample:
            document = self.get_document_content(doc_id, document_collection)
            add_document_id = True
            for idx, fp in enumerate(graph_query):
                subj_sentences, obj_sentences = set(), set()
                for subj in fp.subjects:
                    subj_sentences.update(self.find_sentences_by_entity_id(subj, document))
                #  subj_sentences.update(self.find_sentences_by_entity_name(subj, document))
                for obj in fp.objects:
                    obj_sentences.update(self.find_sentences_by_entity_id(obj, document))
                # obj_sentences.update(self.find_sentences_by_entity_name(obj, document))
                intersection = subj_sentences.intersection(obj_sentences)

                if len(intersection) == 0:
                    add_document_id = False

            if add_document_id:
                document_hits.add(doc_id)
        return calculate_prec_rec_f(document_hits, ids_correct)


class SentenceFactCooccurrence(TextSearchStrategy):

    def __init__(self, document_dir=EXP_TEXTS_DIRECTORY):
        super().__init__(document_dir)
        self.name = "SentenceFactCooccurrence"

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) -> (
            float, float, float):
        graph_query, _ = convert_query_text_to_fact_patterns(query)
        document_hits = set()
        for doc_id in ids_sample:
            document = self.get_document_content(doc_id, document_collection)
            add_document_id = True
            for idx, fp in enumerate(graph_query):
                subj_sentences, obj_sentences = set(), set()
                for subj in fp.subjects:
                    subj_sentences.update(self.find_sentences_by_entity_id(subj, document))
                    subj_sentences.update(self.find_sentences_by_entity_name(subj, document))
                for obj in fp.objects:
                    obj_sentences.update(self.find_sentences_by_entity_id(obj, document))
                    obj_sentences.update(self.find_sentences_by_entity_name(obj, document))
                intersection = subj_sentences.intersection(obj_sentences)
                pred_sentences = set()
                for sent_idx in intersection:
                    sentence_txt = document.sentence_by_id[sent_idx].text.lower().strip()
                    predicate_stemmed = self.stemmer.stem(fp.predicate)
                    if predicate_stemmed in sentence_txt:
                        pred_sentences.add(sent_idx)
                if len(pred_sentences) == 0:
                    add_document_id = False

            if add_document_id:
                document_hits.add(doc_id)
        return calculate_prec_rec_f(document_hits, ids_correct)


class DBSearchStrategy(SearchStrategy):

    def __init__(self, query_engine):
        self.query_engine = query_engine

    def query_ie_database(self, query, document_collection, extraction_type, ids_sample, ids_correct):
        graph_query, _ = convert_query_text_to_fact_patterns(query)
        query_results, _ = self.query_engine.process_query_with_expansion(graph_query, document_collection,
                                                                          extraction_type, query)
        doc_ids = set([q_r.document_id for q_r in query_results])

        if ids_sample:
            doc_hits = doc_ids.intersection(ids_sample)
        else:
            doc_hits = doc_ids
        return calculate_prec_rec_f(doc_hits, ids_correct)


class OpenIESearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'OpenIE'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        return self.query_ie_database(query, document_collection, OPENIE_EXTRACTION, ids_sample, ids_correct)


class OpenIECorefSearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'OpenIECoref'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        return self.query_ie_database(query, document_collection, OPENIE_EXTRACTION, ids_sample, ids_correct)


class PathIESearchStrategy(DBSearchStrategy):

    def __init__(self, query_engine):
        super().__init__(query_engine)
        self.name = 'PathIE'

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) \
            -> (float, float, float):
        return self.query_ie_database(query, document_collection, PATHIE_EXTRACTION, ids_sample, ids_correct)


class KeywordStrategy(TextSearchStrategy):
    def __init__(self, document_dir, mesh_ontology=None):
        super().__init__(document_dir)
        self.mesh_ontology = mesh_ontology
        self.max_distance = math.inf

    def perform_search(self, query: str, document_collection: str, ids_sample: {int}, ids_correct: {int}) -> (
            float, float, float):
        graph_query, _ = convert_query_text_to_fact_patterns(query)

        fps = {fp: (
            {m for s in fp.subjects for m in s.get_meshs()},
            self.stemmer.stem(fp.predicate),
            {m for o in fp.objects for m in o.get_meshs()}
        ) for fp in graph_query}

        hits = set()

        for doc_id in ids_sample:
            doc_content = self.get_document_content(doc_id, document_collection)
            is_hit = True
            for fp in graph_query:
                subs, pred, objs = fp.subjects, fp.predicate, fp.objects
                sub_positions = [pos for s in subs for pos in self.find_entity_positions(s, doc_content)]
                pred_positions = [i.start() for i in re.finditer(self.stemmer.stem(pred), doc_content.content.lower())]
                obj_positions = [pos for o in objs for pos in self.find_entity_positions(o, doc_content)]

                is_hit &= not (not sub_positions or not pred_positions or not obj_positions)

                min_dist = math.inf
                for s_pos, p_pos, o_pos in product(sub_positions, pred_positions, obj_positions):
                    min_dist = min(min_dist, max(abs(s_pos - p_pos), abs(s_pos - o_pos), abs(p_pos - o_pos)))

                is_hit &= min_dist <= self.max_distance

            if is_hit:
                hits.add(doc_id)
        return calculate_prec_rec_f(hits, ids_correct)


class KeywordDistanceStrategy(KeywordStrategy):
    def __init__(self, document_dir, max_distance, mesh_ontology=None):
        super().__init__(document_dir, mesh_ontology)
        self.max_distance = max_distance
