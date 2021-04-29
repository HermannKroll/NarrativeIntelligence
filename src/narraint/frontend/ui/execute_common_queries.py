import logging

from narraint.frontend.ui.search_cache import SearchCache
from narraint.frontend.ui.views import View, convert_query_text_to_fact_patterns

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
    'Metformin treats Diabetes Mellitus. Metformin associated human',
    'Metformin treats Diabetes Mellitus. Metformin associated ?X(Drug)',
    'Metformin treats Diabetes Mellitus. Metformin administered ?X(DosageForm)',
    'Simvastatin induces "Muscular Diseases". ?X(Drug) inhibits cyp3a4',
    '?Drug(Drug) treats ?Dis(Disease)',
    '?Drug(Drug) administered ?Form(DosageForm)'
    'Lidocaine administered ?X(DosageForm)',
    '?X(Drug) administered liposomes',
    '?X(Drug) administered "Nebulizers and Vaporizers"',
    'Vinca associated ?Y(Disease)',
    'Digitalis associated ?Y(Disease)',
    '?X(PlantFamily) associated ?Y(Disease)'
]

DOCUMENT_COLLECTIONS = ['PubMed']  # , 'PMC']


def execute_common_queries():
    cache = SearchCache()
    for q in COMMON_QUERIES:
        logging.info('Caching Query: {}'.format(q))
        query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(q)
        for collection in DOCUMENT_COLLECTIONS:

            results, query_limit_hit = View.instance().query_engine.process_query_with_expansion(query_fact_patterns,
                                                                                                 collection,
                                                                                                 extraction_type="",
                                                                                                 query=q)
            logging.info('Write results to cache...')
            try:
                cache.add_result_to_cache(collection, query_fact_patterns, results, query_limit_hit)
            except Exception:
                logging.error('Cannot store query result to cache...')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    execute_common_queries()


if __name__ == "__main__":
    main()
