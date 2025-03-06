from collections import defaultdict

from kgextractiontoolbox.document.narrative_document import NarrativeDocument
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES


class AnalyzedNarrativeDocument:

    def __init__(self, doc: NarrativeDocument, document_id_art: int, document_id_source: str, collection):
        self.document_id_art = document_id_art
        self.document_id_source = str(document_id_source)
        self.document = doc
        self.collection = collection
        self.concepts = set([t.ent_id for t in doc.tags])
        #    self.concepts.update({t.ent_type for t in doc.tags})
        self.concept2frequency = {}
        self.concept2last_position = {}
        self.concept2first_position = {}
        self.text_len = len(doc.get_text_content(sections=True))
        for t in doc.tags:
            if t.ent_id not in self.concept2frequency:
                self.concept2frequency[t.ent_id] = 1
                self.concept2first_position[t.ent_id] = t.start
                self.concept2last_position[t.ent_id] = t.end
            else:
                self.concept2frequency[t.ent_id] += 1
                self.concept2first_position[t.ent_id] = min(self.concept2first_position[t.ent_id], t.start)
                self.concept2last_position[t.ent_id] = max(self.concept2last_position[t.ent_id], t.end)

        self.max_concept_frequency = max(v for _, v in self.concept2frequency.items())
        self.concept2statement = None
        self.so2statement = None
        self.statement_concepts = None
        self.objects = None
        self.subjects = None
        self.nodes = None
        self.extracted_statements = None

        self.spo2sentences = None
        self.sentence2spo = None
        self.spo2confidences = None
        self.spo2frequency = None
        self.max_statement_frequency = 0
        self.graph = None

    def get_concept_relative_text_position(self, concept):
        # for problematic cases
        if concept in self.concept2last_position:
            return self.concept2last_position[concept] / self.text_len
        else:
            return 0.0

    def get_concept_coverage(self, concept):
        if concept in self.concept2last_position:
            diff = self.concept2last_position[concept] - self.concept2first_position[concept]
            coverage = diff / self.text_len
            # some taggers produced strange tag positions that may exceed the text range
            coverage = max(0.0, min(1.0, coverage))
            return coverage
        else:
            return 0.0

    def prepare_with_min_confidence(self, min_confidence: float = 0):
        self.subjects = set(
            [s.subject_id for s in self.document.extracted_statements if s.confidence >= min_confidence])
        self.objects = set(
            [s.object_id for s in self.document.extracted_statements if s.confidence >= min_confidence])
        self.statement_concepts = set(
            [(s.subject_id, s.object_id) for s in self.document.extracted_statements if s.confidence >= min_confidence])
        self.statement_concepts.update(
            [(s.object_id, s.subject_id) for s in self.document.extracted_statements if s.confidence >= min_confidence])

        self.nodes = self.subjects.union(self.objects)
        self.so2statement = defaultdict(list)
        self.concept2statement = defaultdict(list)
        self.spo2confidences = defaultdict(list)
        self.spo2sentences = dict()
        self.sentence2spo = dict()
        self.spo2frequency = dict()
        self.graph = set()
        for statement in filter(lambda s: s.confidence >= min_confidence, self.document.extracted_statements):
            self.so2statement[(statement.subject_id, statement.object_id)].append(statement)
            self.so2statement[(statement.object_id, statement.subject_id)].append(statement)

            self.concept2statement[statement.subject_id].append(statement)
            self.concept2statement[statement.object_id].append(statement)

            for stmt_ent in [statement.subject_id, statement.object_id]:
                if stmt_ent not in self.concept2frequency:
                    print(f'Warning: {stmt_ent} not in tags of document: {self.document_id_source}')
                    self.concept2frequency[stmt_ent] = 1

            # check both directions if symmetric
            spos = [(statement.subject_id, statement.relation, statement.object_id)]
            if statement.relation in SYMMETRIC_PREDICATES:
                spos.append((statement.object_id, statement.relation, statement.subject_id))

            for spo in spos:
                self.spo2confidences[spo].append(statement.confidence)

                if statement.sentence_id not in self.sentence2spo:
                    self.sentence2spo[statement.sentence_id] = {spo}
                else:
                    self.sentence2spo[statement.sentence_id].add(spo)

                if spo not in self.spo2frequency:
                    self.spo2frequency[spo] = 1
                    self.spo2sentences[spo] = {statement.sentence_id}
                else:
                    self.spo2frequency[spo] += 1
                    self.spo2sentences[spo].add(statement.sentence_id)

                self.graph.add(spo)

        self.extracted_statements = list([s for s in self.document.extracted_statements
                                          if s.confidence >= min_confidence])
        # spo2frequency could be emtpy, take 0.0 in that case
        self.max_statement_frequency = 0.0 if not self.spo2frequency else max(self.spo2frequency.values())

    def get_length_in_words(self):
        text = self.get_text()
        return len(text.split(' '))

    def get_length_in_concepts(self):
        count = 0
        for c, freq in self.concept2frequency.items():
            count += freq
        return count

    def get_concept_frequency(self, concept):
        if concept in self.concept2frequency:
            return self.concept2frequency[concept]
        else:
            return 0

    def get_text(self):
        return self.document.get_text_content(sections=True)

    def to_dict(self):
        return {"document": self.document.to_dict(),
                "concepts": str(self.concepts),
                "concept2frequency": self.concept2frequency}
