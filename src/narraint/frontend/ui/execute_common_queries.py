import logging

from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.frontend.ui.search_cache import SearchCache
from narraint.queryengine.engine import QueryEngine

COMMON_QUERIES = [
    '?X(Method) method Simvastatin',
    '?X(LabMethod) method Simvastatin',
    'Mass Spectrometry method Simvastatin',
    'Simvastatin treats ?X(Disease)',
    'Metformin treats "Diabetes Mellitus"',
    'Simvastatin treats Hypercholesterolemia',
    'Metformin treats ?X(Disease)',
    'Metformin treats ?X(Species)',
    'Metformin administered ?X(DosageForm)',
    'Metformin administered Injections',
    'Metformin inhibits mtor',
    'Metformin inhibits ?X(Target)',
    '?X(Drug) inhibits cyp3a4',
    'cyp3a4 metabolises Simvastatin',
    'Simvastatin induces Rhabdomyolysis',
    'Simvastatin induces Muscular Diseases',
    'Metformin treats Diabetes Mellitus _AND_ Metformin associated human',
    'Metformin treats Diabetes Mellitus _AND_ Metformin associated ?X(Drug)',
    'Metformin treats Diabetes Mellitus _AND_ Metformin administered ?X(DosageForm)',
    'Simvastatin induces "Muscular Diseases" _AND_ ?X(Drug) inhibits cyp3a4',
    '?Drug(Drug) treats ?Dis(Disease)',
    '?Drug(Drug) administered ?Form(DosageForm)',
    'Lidocaine administered ?X(DosageForm)',
    '?X(Drug) administered liposomes',
    '?X(Drug) administered "Nebulizers and Vaporizers"',
    'Vinca associated ?Y(Disease)',
    'Digitalis associated ?Y(Disease)',
    '?X(PlantFamily) associated ?Y(Disease)',
    'Drug treats Covid19',
    'Covid19 method Case Base Studies',
    'Covid 19 method LabMethod',
    'Disease associated Covid19',
    'Covid19 associated ANTINEOPLASTIC AND IMMUNOMODULATING AGENTS',
    'Covid19 associated Human _AND_ Disease associated Human',
    'Covid 19 associated Target',
    'Drug treats Disease',
    'Covid19 associated Vaccine',
    'Covid19 associated Pfizer Covid 19 Vaccine AND Human associated Disease'
]

DOCUMENT_COLLECTIONS = ['PubMed', 'LitCovid', "LongCovid", "ZBMed"]


def execute_common_queries():
    cache = SearchCache()
    translation = QueryTranslation()
    for q in COMMON_QUERIES:
        logging.info('Caching Query: {}'.format(q))
        graph_query, query_trans_string = translation.convert_query_text_to_fact_patterns(q)
        for collection in DOCUMENT_COLLECTIONS:

            results = QueryEngine.process_query_with_expansion(graph_query,
                                                               document_collection_filter={collection})
            logging.info('Write results to cache...')
            try:
                cache.add_result_to_cache(collection, graph_query, results)
            except Exception:
                logging.error('Cannot store query result to cache...')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    execute_common_queries()


if __name__ == "__main__":
    main()
