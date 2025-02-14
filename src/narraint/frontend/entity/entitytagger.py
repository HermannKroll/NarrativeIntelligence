import logging
import string
from typing import List

from sqlalchemy import delete, insert

from narraint.backend.database import SessionExtended
from narraint.backend.models import EntityTaggerData, IndexVersion
from narraint.frontend.entity.entityindexbase import EntityIndexBase
from narrant.entity.entity import Entity


class EntityTagger(EntityIndexBase):
    """
    EntityTagger converts a string to an entity. For that, it performs
    a simple conjunctive like query search (of all terms) and returns the
    corresponding entities.
    """
    __initialized = False

    MINIMUM_CHARACTERS_FOR_TAGGING = 3

    VERSION = 2
    NAME = "EntityTagger"

    def __init__(self):
        if self.__initialized:
            return
        super().__init__()
        logging.info("Initialize EntityTagger...")

        # we need the space for correct handling of partial term matching
        trans_map = {p: ' ' for p in string.punctuation}
        self.__translator = str.maketrans(trans_map)
        self.__db_values_to_insert = list()

        if not self._validate_index():
            self.store_index()
        self.__initialized = True

    def _validate_index(self) -> bool:
        session = SessionExtended.get()

        # retrieve current version if present
        index_version = None
        query = session.query(IndexVersion).filter(IndexVersion.name == self.NAME)
        if query.count() > 0:
            index_version = query.first().version

        # retrieve length of database index
        index_count = session.query(EntityTaggerData).count()

        if (index_version is None
                or index_version != self.VERSION
                or index_count == 0):
            logging.info("Index empty or outdated.")
            return False
        return True

    def _prepare_string(self, term: str) -> str:
        term = term.strip().lower().translate(self.__translator).strip()
        # remove double white spaces
        while '  ' in term:
            term = term.replace('  ', ' ')
        return term

    def store_index(self):
        logging.info('Creating index for EntityTagger...')

        # delete old index entries
        session = SessionExtended.get()
        session.execute(delete(EntityTaggerData))
        session.commit()

        self._create_index()
        logging.info(f'Inserting {len(self.__db_values_to_insert)} values into database...')
        EntityTaggerData.bulk_insert_values_into_table(session, self.__db_values_to_insert)

        # update new EntityTagger index
        session.execute(delete(IndexVersion).where(IndexVersion.name == EntityTagger.NAME))
        session.execute(insert(IndexVersion).values(name=EntityTagger.NAME, version=EntityTagger.VERSION))
        session.commit()
        session.remove()

        self.__db_values_to_insert.clear()
        logging.info('Finished')

    def _add_term(self, term, entity_id: str, entity_type: str, entity_class: str = None):
        synonym = term.strip().lower()
        if synonym is None:
            return

        self.__db_values_to_insert.append(dict(entity_id=entity_id,
                                               entity_type=entity_type,
                                               entity_class=entity_class,
                                               synonym=synonym,
                                               # space is important for matching
                                               synonym_processed=' ' + self._prepare_string(term)))

    def tag_entity(self, term: str) -> List[Entity]:
        # first process the string
        term = self._prepare_string(term)

        # ignore to short terms -> no matches
        if not term or len(term) < EntityTagger.MINIMUM_CHARACTERS_FOR_TAGGING:
            raise KeyError('Does not know an entity for term: {}'.format(term))

        session = SessionExtended.get()
        query = session.query(EntityTaggerData)
        # Construct the query as a disjunction with like expressions
        # e.g. the search covid 19 is performed by
        # WHERE synonym like '% covid%' AND synonym like '% 19%'
        # SQL alchemy overloads the bitwise & operation to connect different expressions via AND
        filter_exp = None
        for part in term.split(' '):
            part = part.strip()
            if not part:
                continue
            # a synonym could match the term at the beginning but not in between
            # eg all words that start with diab are valid matches
            # but synonyms like hasdiabda are not matches
            if filter_exp is None:
                filter_exp = EntityTaggerData.synonym_processed.like('% {}%'.format(part))
            else:
                filter_exp = filter_exp & EntityTaggerData.synonym_processed.like('% {}%'.format(part))
        query = query.filter(filter_exp)

        entities = []
        known_entities = set()

        for result in query:
            cleaned_synonym = result.synonym.strip()  # remove leading space
            key = (result.entity_id, result.entity_type, cleaned_synonym)
            if key in known_entities:
                continue
            entities.append(Entity(entity_name=cleaned_synonym,
                                   entity_id=result.entity_id,
                                   entity_type=result.entity_type,
                                   entity_class=result.entity_class))
            known_entities.add(key)
        session.remove()

        if len(entities) == 0:
            raise KeyError('Does not know an entity for term: {}'.format(term))
        return entities

    @staticmethod
    def known_terms():
        logging.info("Querying known terms...")
        known_terms = dict()

        session = SessionExtended.get()
        query = session.query(EntityTaggerData.synonym, EntityTaggerData.entity_type)

        for synonym in query:
            term = synonym[0].strip()
            entity_type = synonym[1].strip()

            if term not in known_terms:
                known_terms[term] = {entity_type}
            else:
                known_terms[term].add(entity_type)
        return known_terms


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    entity_tagger = EntityTagger()
    tests = ['covid', 'covid 19', 'melanoma', 'braf']
    for test in tests:
        print()
        for e in entity_tagger.tag_entity(test)[:4]:
            print(e.entity_id, e.entity_type, e.entity_name, e.entity_class)


if __name__ == "__main__":
    main()
