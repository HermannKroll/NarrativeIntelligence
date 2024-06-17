from kgextractiontoolbox.document.narrative_document import NarrativeDocument, StatementExtraction
from narrant.cleaning.pharmaceutical_vocabulary import SYMMETRIC_PREDICATES


class IndexedDocument(NarrativeDocument):
    """
    Class that represents a narrative document with generated index data,
    e.g., entity2frequency
    """

    def __init__(self, nd: NarrativeDocument):
        super().__init__(document_id=nd.id, title=nd.title, abstract=nd.abstract,
                         metadata=nd.metadata, tags=nd.tags, sentences=nd.sentences,
                         extracted_statements=nd.extracted_statements)

        self.extracted_statements = [s for s in self.extracted_statements if s.relation]
        self.classification = nd.classification

        self.spo2confidence = {}

        self.entity2frequency = {}
        self.entity2last_position = {}
        self.entity2first_position = {}
        self.text_len = len(self.get_text_content(sections=True))
        self.concept_count = len(self.tags)
        for t in self.tags:
            key = (t.ent_type, t.ent_id)

            if key not in self.entity2frequency:
                self.entity2frequency[key] = 1
                self.entity2first_position[key] = t.start
                self.entity2last_position[key] = t.end
            else:
                self.entity2frequency[key] += 1
                self.entity2first_position[key] = min(self.entity2first_position[key], t.start)
                self.entity2last_position[key] = max(self.entity2last_position[key], t.end)

        if len(self.entity2frequency) > 0:
            self.max_concept_frequency = max(v for _, v in self.entity2frequency.items())
        else:
            self.max_concept_frequency = 0

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
                    if spo in self.spo2confidence:
                        self.spo2confidence[spo] = max(self.spo2confidence[spo], statement.confidence)
                    else:
                        self.spo2confidence[spo] = statement.confidence

    def get_statement_confidence(self, statement: StatementExtraction) -> float:
        """
        Get the confidence of a statement (max confidence of all of its extractions)
        :param statement: a statement
        :return:
        """
        key = (statement.object_type, statement.object_id,
               statement.relation,
               statement.subject_type, statement.subject_id)
        if key in self.spo2confidence:
            return self.spo2confidence[key]
        else:
            return 0.0

    def get_entity_coverage(self, entity_type: str, entity_id: str) -> float:
        """
        Computes the coverage of an entity within a document
        coverage = (last_pos - first_pos) / text_len
        :param entity_type: the entity type
        :param entity_id: the entity type
        :return: coverage score [0, 1]
        """
        key = (entity_type, entity_id)
        if key in self.entity2last_position:
            diff = self.entity2last_position[key] - self.entity2first_position[key]
            coverage = diff / self.text_len
            # some taggers produced strange tag positions that may exceed the text range
            coverage = max(0.0, min(1.0, coverage))
            return coverage
        else:
            return 0.0

    def get_entity_tf(self, entity_type: str, entity_id: str) -> int:
        """
        Get the frequency of an entity within this document
        :param entity_type: the entity type
        :param entity_id: the entity id
        :return: the frequency as an integer
        """
        key = (entity_type, entity_id)
        if key in self.entity2frequency:
            return self.entity2frequency[key]
        else:
            # some strange concepts do not appear as tags although they are used on graphs
            return 1
