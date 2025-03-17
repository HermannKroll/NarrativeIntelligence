from collections import defaultdict

from kgextractiontoolbox.document.narrative_document import NarrativeDocument
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES
from narrant.entity.entityidtranslator import EntityIDTranslator


def get_unique_entity_key(entity_type: str, entity_id: str) -> str:
    """
    Generates a unique entity key as a string
    :param entity_type: entity type
    :param entity_id: entity id
    :return: str
    """
    return '___'.join([entity_type, entity_id])


class ScoredDocumentEntity:
    """
    Scored document entity contains the entity type and id of some entity within a document
    Scores like tf, tf_normalized and coverage can be stored
    """

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.tf = None
        self.tf_normalized = None
        self.coverage = None
        self.score = None

    def set_score(self, score: float):
        self.score = score

    def set_frequency(self, frequency: int, max_entity_count: int):
        self.tf = frequency
        self.tf_normalized = float(frequency) / float(max_entity_count)

    def set_coverage(self, first_pos: int, last_pos: int, text_len: int):
        diff = last_pos - first_pos
        coverage = float(diff) / float(text_len)
        # some taggers produced strange tag positions that may exceed the text range
        self.coverage = max(0.0, min(1.0, coverage))

    def get_unique_key(self):
        return get_unique_entity_key(entity_type=self.entity_type, entity_id=self.entity_id)

    def __hash__(self):
        return hash(self.get_unique_key())

    def __eq__(self, other):
        return self.get_unique_key() == other.get_unique_key()


class ScoredDocumentStatement:
    """
    Class that represents a scored document statement
    """

    def __init__(self, subject: ScoredDocumentEntity, relation: str, object: ScoredDocumentEntity):
        self.subject = subject
        self.relation = relation
        self.object = object
        self.confidence = None
        self.score = None

    def set_confidence(self, confidence: float):
        assert 0.0 <= confidence <= 1.0
        self.confidence = confidence

    def set_score(self, score: float):
        self.score = score

    def has_equal_entities(self, other) -> bool:
        """
        Test whether two scored document statement have equal entities (either s1=s2 && o1=o2) or (s1=o2) and (o1=s2)
        :param other:
        :return:
        """
        return (self.subject.get_unique_key() == other.subject.get_unique_key() and
                self.object.get_unique_key() == other.object.get_unique_key()) or \
            (self.object.get_unique_key() == other.subject.get_unique_key() and
             self.subject.get_unique_key() == other.object.get_unique_key())

    def get_unique_key(self):
        return '___'.join([self.subject.get_unique_key(), self.relation, self.object.get_unique_key()])

    def __hash__(self):
        return hash(self.get_unique_key())

    def __eq__(self, other):
        return self.get_unique_key() == other.get_unique_key()


class IndexedDocument(NarrativeDocument):
    """
    Class that represents a narrative document with generated index data,
    """

    def __init__(self, nd: NarrativeDocument):
        super().__init__(document_id=nd.id, title=nd.title, abstract=nd.abstract,
                         metadata=nd.metadata, tags=nd.tags, sentences=nd.sentences,
                         extracted_statements=nd.extracted_statements)

        self.first_stage_score = None
        self.extracted_statements = [s for s in self.extracted_statements if s.relation]
        self.extracted_statements = [s for s in self.extracted_statements if s.subject_type != s.object_type]
        self.classification = nd.classification

        self.scored_entities: [ScoredDocumentEntity] = set()
        self.max_entity_frequency = 0
        self.text_len = len(self.get_text_content(sections=True))
        self.compute_scored_entity_information()
        self.entity_key2scored_entity = {e.get_unique_key(): e for e in self.scored_entities}

        self.scored_statements: [ScoredDocumentStatement] = set()
        self.compute_scored_statement_information()

    def compute_scored_entity_information(self):
        entity2frequency = {}
        entity2last_position = {}
        entity2first_position = {}
        # singleton implementation
        entityidtranslator = EntityIDTranslator()
        for t in self.tags:
            # translate gene ids to symbols to be compatible to statement gene representation
            translated_id = entityidtranslator.translate_entity_id(t.ent_id, t.ent_type)
            e = ScoredDocumentEntity(entity_type=t.ent_type, entity_id=translated_id)
            self.scored_entities.add(e)
            entity_key = e.get_unique_key()
            if entity_key not in entity2frequency:
                entity2frequency[entity_key] = 1
                entity2first_position[entity_key] = t.start
                entity2last_position[entity_key] = t.end
            else:
                entity2frequency[entity_key] += 1
                entity2first_position[entity_key] = min(entity2first_position[entity_key], t.start)
                entity2last_position[entity_key] = max(entity2last_position[entity_key], t.end)

        if len(entity2frequency) > 0:
            self.max_entity_frequency = max(v for _, v in entity2frequency.items())

        for e in self.scored_entities:
            e.set_frequency(frequency=entity2frequency[e.get_unique_key], max_entity_count=self.max_entity_frequency)
            e.set_coverage(first_pos=entity2first_position[e.get_unique_key],
                           last_pos=entity2last_position[e.get_unique_key],
                           text_len=self.text_len)

    def compute_scored_statement_information(self):
        spo2confidence = defaultdict(list)

        if self.extracted_statements:
            for statement in self.extracted_statements:
                spos = [(statement.subject_type, statement.subject_id,
                         statement.relation,
                         statement.object_type, statement.object_id)]
                if statement.relation in SYMMETRIC_PREDICATES:
                    spos.append((statement.object_type, statement.object_id,
                                 statement.relation,
                                 statement.subject_type, statement.subject_id))

                for spo in spos:
                    if spo in spo2confidence:
                        spo2confidence[spo] = max(spo2confidence[spo], statement.confidence)
                    else:
                        spo2confidence[spo] = statement.confidence

        for (subject_type, subject_id, relation, object_type, object_id) in spo2confidence:
            subject_key = get_unique_entity_key(entity_type=subject_type, entity_id=subject_id)
            object_key = get_unique_entity_key(entity_type=object_type, entity_id=object_id)
            self.scored_statements.add(ScoredDocumentStatement(subject=self.entity_key2scored_entity[subject_key],
                                                               relation=relation,
                                                               object=self.entity_key2scored_entity[object_key]))
