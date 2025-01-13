import logging
import string
from collections import defaultdict

from sqlalchemy import delete, insert

from narraint.backend.database import SessionExtended
from narraint.backend.models import EntityExplainerData, IndexVersion
from narraint.frontend.entity.entityindexbase import EntityIndexBase
from narraint.frontend.entity.entitytagger_db import EntityTaggerDB
from narrant.entity.entityresolver import EntityResolver


class EntityExplainerDB(EntityIndexBase):
    __initialized = False

    VERSION = 1
    NAME = "EntityExplainerDB"

    def __init__(self):
        if self.__initialized:
            return

        super().__init__()

        logging.info('Initialize EntityExplainerDB...')
        self.expand_by_subclasses = False
        self.entity2terms = defaultdict(set)
        self.version = None
        trans_map = {p: '' for p in string.punctuation}
        self.__translator = str.maketrans(trans_map)

        if not self._validate_index():
            self.store_index()
        self.__initialized = True

    def store_index(self):
        logging.info('Creating index for EntityExplainerDB...')

        # delete old index entries
        session = SessionExtended.get()
        session.execute(delete(EntityExplainerData))
        session.commit()

        self._create_index()

        entries = list()
        for entity_id, entity_terms in sorted(self.entity2terms.items(), key=lambda x: x[0]):
            if entity_id.strip() == "":
                continue
            terms = EntityExplainerData.synonyms_to_string(list(entity_terms))
            entries.append(dict(entity_id=entity_id, entity_terms=terms))
        logging.info(f'Inserting {len(self.entity2terms)} values into database...')
        EntityExplainerData.bulk_insert_values_into_table(session, entries)

        # update new EntityTaggerDB index
        session.execute(delete(IndexVersion).where(IndexVersion.name == EntityExplainerDB.NAME))
        session.execute(insert(IndexVersion).values(name=EntityExplainerDB.NAME, version=EntityExplainerDB.VERSION))
        session.commit()
        session.remove()

        self.entity2terms.clear()
        logging.info('Finished')

    def _validate_index(self) -> bool:
        session = SessionExtended.get()

        # retrieve current version if present
        index_version = None
        query = session.query(IndexVersion).filter(IndexVersion.name == self.NAME)
        if query.count() > 0:
            index_version = query.first().version

        # retrieve length of database index
        index_count = session.query(EntityExplainerData).count()

        if (index_version is None
                or index_version != self.VERSION
                or index_count == 0):
            logging.info("Index empty or outdated.")
            return False
        return True

    def _add_term(self, term, entity_id: str, entity_type: str, entity_class: str = None):
        self.entity2terms[entity_id].add(term.strip())

    def get_prefixes(self, name):
        words = list([n for n in name.translate(self.__translator).lower().split(' ')])
        for i in range(len(words), 0, -1):
            yield ' '.join([k for k in words[:i]])

    def filter_names_for_prefix_duplicates(self, names):
        selected_headings = []
        known_prefixes = set()
        for h in names:
            already_selected = False

            h_prefixes = list(self.get_prefixes(h))
            for prefix in h_prefixes:
                if prefix in known_prefixes:
                    already_selected = True
                    break

            # Skip word. A prefix word has already been selected
            if already_selected:
                continue

            known_prefixes.add(h.translate(self.__translator).lower())
            selected_headings.append(h)

        return selected_headings

    def explain_entities(self, entities, truncate_at_k=25):
        resolver = EntityResolver()
        headings = set()
        # Add all headings and known terms for the possible entity ids
        for entity in entities:
            heading = resolver.get_name_for_var_ent_id(entity.entity_id, entity.entity_type, resolve_gene_by_id=False)
            headings.add(heading)

            session = SessionExtended.get()
            query = session.query(EntityExplainerData.entity_terms)
            query = query.filter(entity.entity_id == EntityExplainerData.entity_id)

            if query.count() == 0:
                continue
            terms = query.first()[0]
            terms = EntityExplainerData.string_to_synonyms(terms)
            headings |= set(terms)

        # Convert it to a list and sort
        headings = list([h for h in headings if len(h) > 1])
        headings.sort()

        # Remove headings that have the same prefix
        headings = self.filter_names_for_prefix_duplicates(headings)

        heading_len = len(headings)
        if heading_len > truncate_at_k:
            headings = headings[:truncate_at_k]
            headings.append(f"and {heading_len - truncate_at_k} more")

        return headings

    def explain_entity_str(self, entity_str, truncate_at_k=25):
        tagger = EntityTaggerDB()
        entities = tagger.tag_entity(entity_str)
        return self.explain_entities(entities, truncate_at_k=truncate_at_k)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    entity_explainer = EntityExplainerDB()
    explanations = entity_explainer.explain_entity_str("metformin")
    print(explanations)

    entity_tagger_db = EntityTaggerDB()
    tags = entity_tagger_db.tag_entity("metformin")
    print(tags)


if __name__ == "__main__":
    main()
