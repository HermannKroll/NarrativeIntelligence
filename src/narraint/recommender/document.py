from collections import defaultdict

from kgextractiontoolbox.document.narrative_document import NarrativeDocument
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES


class RecommenderDocument(NarrativeDocument):

    def __init__(self, nd: NarrativeDocument):
        super().__init__(document_id=nd.id, title=nd.title, abstract=nd.abstract,
                         metadata=nd.metadata, tags=nd.tags, sentences=nd.sentences,
                         extracted_statements=nd.extracted_statements)

        self.first_stage_score = None
        self.extracted_statements = [s for s in self.extracted_statements if s.relation]
        self.extracted_statements = [s for s in self.extracted_statements if s.subject_type != s.object_type]

        self.classification = nd.classification

        self.spo2confidences = defaultdict(list)
        self.spo2frequency = dict()
        self.spo2sentences = dict()
        self.sentence2spo = dict()
        self.graph = set()
        self.nodes = set()
        self.statement_concept2frequency = dict()
        self.concept2frequency = dict()
        self.concepts = set()

        self.concept2frequency = {}
        self.concept2last_position = {}
        self.concept2first_position = {}
        self.text_len = len(self.get_text_content(sections=True))
        self.concept_count = len(self.tags)
        for t in self.tags:
            self.concepts.add((t.ent_id, t.ent_type))
            if t.ent_id not in self.concept2frequency:
                self.concept2frequency[t.ent_id] = 1
                self.concept2first_position[t.ent_id] = t.start
                self.concept2last_position[t.ent_id] = t.end
            else:
                self.concept2frequency[t.ent_id] += 1
                self.concept2first_position[t.ent_id] = min(self.concept2first_position[t.ent_id], t.start)
                self.concept2last_position[t.ent_id] = max(self.concept2last_position[t.ent_id], t.end)

        if len(self.concept2frequency) > 0:
            self.max_concept_frequency = max(v for _, v in self.concept2frequency.items())
        else:
            self.max_concept_frequency = 0

        if self.extracted_statements:
            for statement in self.extracted_statements:
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

                    for concept in [statement.subject_id, statement.object_id]:
                        if concept in self.statement_concept2frequency:
                            self.statement_concept2frequency[concept] += 1
                        else:
                            self.statement_concept2frequency[concept] = 1

                    self.graph.add(spo)
                    self.nodes.add(statement.subject_id)
                    self.nodes.add(statement.object_id)

            self.max_statement_frequency = max(self.spo2frequency.values())

    def get_concept_relative_text_position(self, concept):
        # for problematic caseses
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


    def get_concept_tf(self, concept):
        if concept in self.concept2frequency:
            return self.concept2frequency[concept]
        else:
            # some strange concepts do not appear as tags although they are used on graphs
            return 1

    def set_first_stage_score(self, score):
        self.first_stage_score = score
