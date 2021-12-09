import json
import logging

from narraint.backend.database import SessionExtended
from narraint.backend.models import retrieve_narrative_documents_from_database
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.engine import QueryEngine

queries = [
    ("q1", "Metformin treats Diabetes Mellitus"),
    ("q2", "Aspirin treats Headaches"),
    ("q3", "Simvastatin induces Rhabdomyolysis")
]

document_collection = "PubMed"


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    entity_tagger = EntityTagger.instance()
    translation = QueryTranslation()

    session = SessionExtended.get()
    for query_name, query in queries:
        graph_query, query_trans_string = translation.convert_query_text_to_fact_patterns(query)
        # run query
        results = QueryEngine.process_query_with_expansion(graph_query, document_collection_filter={"PubMed"})
        result_ids = {r.document_id for r in results}

        narrative_documents = retrieve_narrative_documents_from_database(session=session, document_ids=result_ids,
                                                                         document_collection=document_collection)
        data = [d.to_dict() for d in narrative_documents]
        with open(f'{query_name}.json', 'w') as f:
            json.dump(data, f)


if __name__ == "__main__":
    main()
