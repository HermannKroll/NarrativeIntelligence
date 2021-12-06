import json
import logging
from argparse import ArgumentParser
from datetime import datetime

from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, Tag, DocumentMetadata, DocumentTranslation
from narrant.entity.meshontology import MeSHOntology
from narrant.preprocessing.enttypes import GENE, DISEASE
from narrant.progress import Progress
from narrant.pubtator.document import TaggedEntity, TaggedDocument

ZBMED_BULK_INSERT_AFTER_K = 1000


def derive_ent_id_and_type_from_concept_str(concept_str: str, concept_class: str) -> [str, str]:
    """
    Derives the entity id and entity type from the ZBMed concept str
    Works for MeSH and HGCN (Genes) now
    :param concept_str: the ZBMed concept str
    :param concept_class: the ZBMed concept class
    :return:
    """
    e_id = concept_str.split('/')[-1]

    # ignored classes
    if 'uniprot' in concept_str or "zbmed" in concept_str:
        return None, None

    if concept_class == 'MESHD':
        mesh_ontology = MeSHOntology.instance()
        # its a mesh class
        try:
            e_types = mesh_ontology.get_entity_types_for_descriptor(e_id)
        except KeyError:
            return None, None

        e_id = f'MESH:{e_id}'
        if len(e_types) == 0 or len(e_types) > 1:
            if "Disease" in e_types:
                return e_id, DISEASE
            else:
                raise ValueError(f'Cannot find a unique entity type for MeSH descriptor: {e_id}')
        return e_id, e_types[0]
    elif concept_class == 'HGNC':
        # ids look like HGNC:6023
        e_id = e_id.split(':')[1]
        return e_id, GENE
    else:
        raise ValueError(f'Cannot decode concept: {concept_str} with class {concept_class}')


def zbmed_load_json_file_to_database(json_file: str, document_collection: str) -> None:
    """
    Loads the ZBMed JSON file to the database
    Extracts information for the following tables: Document, DocumentTranslation, Tag and DocumentMetadata
    :param json_file: path to the ZBMed json file
    :param document_collection: the corresponding document collection
    :return: None
    """
    logging.info('Loading ZBMed json file...')
    with open(json_file, 'rt') as fp:
        json_data = json.load(fp)

    logging.info('Iterating over JSON content...')
    progress = Progress(total=len(json_data["content"]), print_every=100, text="Loading ZBMed data")
    progress.start_time()

    session = SessionExtended.get()
    logging.info(f'Querying known source ids for document collection: {document_collection}')
    known_source_ids = set()
    q = session.query(DocumentTranslation.document_id, DocumentTranslation.source_doc_id) \
        .filter(DocumentTranslation.document_collection == document_collection).distinct()
    last_known_translated_id = 0
    for row in q:
        if row[0] > last_known_translated_id:
            last_known_translated_id = row[0]
        known_source_ids.add(row[1])

    logging.info(f'{len(known_source_ids)} source ids are already known. '
                 f'Last highest document id was: {last_known_translated_id}')
    doc_inserts, tag_inserts, metadata_inserts, doc_translation_inserts = [], [], [], []
    for idx, doc in enumerate(json_data["content"]):
        progress.print_progress(idx)
        art_doc_id = idx + (last_known_translated_id + 1)

        doc_original_id = doc["id"]
        # skip known source ids
        if doc_original_id in known_source_ids:
            continue

        title = doc["title"]
        abstract = doc["abstract"]

        if not title and not abstract:
            continue

        authors = ' | '.join([str(a) for a in doc["authors"]])
        # dates look like '2020-07-13T00:00:00'
        publication_date = datetime.strptime(str(doc["date"]).split('T')[0], "%Y-%m-%d")
        publication_year = publication_date.year
        publication_month = publication_date.month

        publication_link = doc["docLink"]
        # source = journal
        publication_journal = doc["source"]

        # now load the annotations
        entity_annotations = []
        for anno in doc["title_annotations"]:
            a_class = anno["class"]
            a_concept = anno["concept"]
            a_start = anno["offset"]["start"]
            a_end = anno["offset"]["end"]
            a_text = title[a_start:a_end]
            e_id, e_type = derive_ent_id_and_type_from_concept_str(a_concept, a_class)
            if e_id and e_type:
                entity_annotations.append(TaggedEntity(document=art_doc_id, start=a_start, end=a_end,
                                                       ent_type=e_id, ent_id=e_type, text=a_text))

        title_offset = len(title)
        for anno in doc["abstract_annotations"]:
            a_class = anno["class"]
            a_concept = anno["concept"]
            a_start = anno["offset"]["start"]
            a_end = anno["offset"]["end"]
            a_text = abstract[a_start:a_end]

            e_id, e_type = derive_ent_id_and_type_from_concept_str(a_concept, a_class)
            if e_id and e_type:
                entity_annotations.append(TaggedEntity(document=art_doc_id, start=a_start + title_offset,
                                                       end=a_end + title_offset,
                                                       ent_type=e_id, ent_id=e_type, text=a_text))

        tagged_doc = TaggedDocument(title=title, abstract=abstract, id=art_doc_id)
        tagged_doc.tags = entity_annotations
        tagged_doc.sort_tags()

        doc_inserts.append(dict(id=art_doc_id,
                                collection=document_collection,
                                title=title,
                                abstract=abstract))

        content = tagged_doc.get_text_content()
        doc_translation_inserts.append(dict(document_id=art_doc_id,
                                            document_collection=document_collection,
                                            source_doc_id=doc_original_id,
                                            md5=DocumentTranslation.text_to_md5_hash(content),
                                            source=publication_link,
                                            date_inserted=datetime.now()))

        for tag in tagged_doc.tags:
            tag_inserts.append(dict(document_id=art_doc_id,
                                    document_collection=document_collection,
                                    ent_id=tag.ent_id,
                                    ent_type=tag.ent_type,
                                    start=tag.start,
                                    end=tag.end,
                                    ent_str=tag.text))

        metadata_inserts.append(dict(document_id=art_doc_id,
                                     document_collection=document_collection,
                                     document_id_original=doc_original_id,
                                     authors=authors,
                                     journals=publication_journal,
                                     publication_year=publication_year,
                                     publication_month=publication_month,
                                     publication_doi=publication_link))

        if (idx + 1) % ZBMED_BULK_INSERT_AFTER_K == 0:
            Document.bulk_insert_values_into_table(session, doc_inserts)
            DocumentTranslation.bulk_insert_values_into_table(session, doc_translation_inserts)
            Tag.bulk_insert_values_into_table(session, tag_inserts)
            DocumentMetadata.bulk_insert_values_into_table(session, metadata_inserts)

            doc_inserts.clear()
            doc_translation_inserts.clear()
            tag_inserts.clear()
            metadata_inserts.clear()

    # Insert remaining
    Document.bulk_insert_values_into_table(session, doc_inserts)
    DocumentTranslation.bulk_insert_values_into_table(session, doc_translation_inserts)
    Tag.bulk_insert_values_into_table(session, tag_inserts)
    DocumentMetadata.bulk_insert_values_into_table(session, metadata_inserts)

    doc_inserts.clear()
    doc_translation_inserts.clear()
    tag_inserts.clear()
    metadata_inserts.clear()
    logging.info('Finished')


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="ZBMed JSON file")
    parser.add_argument("-c", "--collection", required=True, help="Name of the document collection")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    zbmed_load_json_file_to_database(args.input, document_collection=args.collection)


if __name__ == "__main__":
    main()
