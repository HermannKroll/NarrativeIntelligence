import argparse
import logging

from kgextractiontoolbox.backend.database import Session
from kgextractiontoolbox.backend.models import Predication
from kgextractiontoolbox.cleaning.relation_vocabulary import RelationVocabulary
from narraint.config import PHARM_RELATION_VOCABULARY
from narraint.queryengine.query_hints import PREDICATE_TYPING, SYMMETRIC_PREDICATES, PREDICATE_EXPANSION
from narrant.entity.meshontology import MeSHOntology


def export_database_to_edb_predicates(path: str):
    logging.info(f'Exporting files to {path} ...')
    session = Session.get()

    logging.info('Writing predicates...')
    relation_vocab = RelationVocabulary()
    relation_vocab.load_from_json(PHARM_RELATION_VOCABULARY)
    allowed_predicates = set(relation_vocab.relation_dict.keys())
    with open("predicate.csv", 'wt') as f:
        for p in allowed_predicates:
            f.write(f'{p}\n')

    logging.info('Writing symmetric predicates...')
    with open("symmetricpredicate.csv", 'wt') as f:
        for p in SYMMETRIC_PREDICATES:
            f.write(f'{p}\n')

    logging.info('Writing hierarchical predicates...')
    with open("hierarchicalpredicate.csv", 'wt') as f:
        for p, ps_exp in PREDICATE_EXPANSION.items():
            for p2 in ps_exp:
                f.write(f'{p},{p2}\n')
        for p in allowed_predicates:
            if p != "associated":
                f.write(f'associated,{p}\n')

    logging.info('Retrieving subjects from database...')
    subject_ent_query = session.query(Predication.subject_id, Predication.subject_type).distinct()
    entities = {(r[1], r[0]) for r in subject_ent_query}
    logging.info('Retrieving objects from database...')
    object_ent_query = session.query(Predication.object_id, Predication.object_type).distinct()
    entities.update({(r[1], r[0]) for r in object_ent_query})
    logging.info(f'Writing {len(entities)} entities...')
    with open("entity.csv", 'wt') as f:
        for e in entities:
            # encode type into entity string to be unique
            e_write = f'{e[0]}_{e[1]}'.replace('"', '')
            f.write(f'"{e_write}"\n')

    with open("class.csv", 'wt') as f:
        for e in entities:
            # encode type into entity string to be unique
            e_write = f'{e[0]}_{e[1]}'.replace('"', '')
            f.write(f'"class_{e_write}"\n')

    logging.info(f'Writing {len(entities)} entity to class...')
    with open("entitytoclass.csv", 'wt') as f:
        for e in entities:
            e_write = f'{e[0]}_{e[1]}'.replace('"', '')
            f.write(f'"{e_write}","class_{e_write}"\n')

    logging.info('Preparing subclass relations...')
    entities_with_mesh = {e for e in entities if e[1].startswith('MESH:D')}
    logging.info(f'{len(entities_with_mesh)} entities are in the MeSH Ontology...')
    mesh = MeSHOntology.instance()
    logging.info(f'Writing subclasses...')
    ignored = set()
    exported_subclasses = set()
    with open("subclass.csv", 'wt') as f:
        for e_type, e_id in entities_with_mesh:
            e_str = f'class_{e_type}_{e_id}'.replace('"', '')
            try:
                for e_subclass, _ in mesh.retrieve_subdescriptors(e_id.replace('MESH:', '')):
                    e_subclass_str = f'class_{e_type}_MESH:{e_subclass}'.replace('"', '')
                    key = (e_subclass_str, e_str)
                    if key not in exported_subclasses:
                        f.write(f'"{e_subclass_str}","{e_str}"\n')
                        exported_subclasses.add(key)
            except KeyError:
                ignored.add(e_id)
    if len(ignored) > 0:
        logging.info(f'Ignored the following entities: {ignored}')

    logging.info('Retrieving document contexts...')
    doc_query = session.query(Predication.document_id, Predication.document_collection)
    documents = {f'{r[1]}_{r[0]}' for r in doc_query}
    logging.info(f'Writing {len(documents)} contexts to file...')
    with open("context.csv", 'wt') as f:
        for d in documents:
            f.write(f'"{d}"\n')

    logging.info('Retrieving statements and writing to file...')
    statement_query = session.query(Predication).yield_per(1000000)
    exported_statements = set()
    with open("statement.csv", 'wt') as f:
        for r in statement_query:
            context = f'{r.document_collection}_{r.document_id}'
            sub = f'{r.subject_type}_{r.subject_id}'.replace('"', '')
            rel = r.relation
            obj = f'{r.object_type}_{r.object_id}'.replace('"', '')
            key = (context, sub, rel, obj)
            if key not in exported_statements:
                f.write(f'"{sub}","{rel}","{obj}","{context}"\n')
                exported_statements.add(key)

    logging.info('Finished')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to directory in which the files should be created")
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    export_database_to_edb_predicates(args.path)


if __name__ == "__main__":
    main()
