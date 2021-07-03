import logging
from collections import defaultdict
from datetime import datetime

from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.engine import QueryEngine

COMMON_QUERIES = [
    'Metformin administered Injections',
    "Metformin treats ?X(Disease) _AND_ ?X(Disease) associated Human",
    'Simvastatin induces Rhabdomyolysis',
    'Mass Spectrometry method Simvastatin',
    'Simvastatin associated human',
    'Metformin associated human',
    'Metformin treats "Diabetes Mellitus"',
    'Metformin treats Diabetes Mellitus _AND_ Metformin associated human',
    'Simvastatin treats Diabetes Mellitus _AND_ Simvastatin associated human',
    'Amiodarone treats Diabetes Mellitus _AND_ Amiodarone associated human',
    'Metformin treats Diabetes Mellitus _AND_ Metformin associated ?X(Drug)',
    '?X(Method) method Simvastatin',
    '?X(LabMethod) method Simvastatin',
    'Simvastatin treats ?X(Disease)',
    'Metformin treats "Diabetes Mellitus"',
    'Simvastatin treats Hypercholesterolemia',
    'Metformin treats ?X(Disease)',
    'Metformin treats ?X(Species)',
    'Metformin administered ?X(DosageForm)',
    'Metformin inhibits mtor',
    'Metformin inhibits ?X(Target)',
    '?X(Drug) inhibits cyp3a4',
    'cyp3a4 metabolises Simvastatin',
    'Simvastatin induces Muscular Diseases',
    'Metformin treats Diabetes Mellitus _AND_ Metformin associated human',
    'Metformin treats Diabetes Mellitus _AND_ Metformin associated ?X(Drug)',
    'Metformin treats Diabetes Mellitus _AND_ Metformin administered ?X(DosageForm)',
    'Simvastatin induces "Muscular Diseases" _AND_ ?X(Drug) inhibits cyp3a4',
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


def main():
    """
    Performes the performance evaluation and stores the results as .tsv files
    """
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    translation = QueryTranslation()
    query_engine = QueryEngine()
    for q in COMMON_QUERIES:
        logging.info('Executing Query: {}'.format(q))
        query_fact_patterns, query_trans_string = translation.convert_query_text_to_fact_patterns(q)
        logging.info(f'Translated Query is: {query_fact_patterns}')
        for collection in DOCUMENT_COLLECTIONS:
            new_time = datetime.now()
            results_new, query_limit_hit = query_engine.process_query_with_expansion(query_fact_patterns)
            new_time = datetime.now() - new_time
            result_new_ids = {r.document_id for r in results_new}
            logging.info(f'Found {len(results_new)} result with new query')
            logging.info(f'New time: {new_time}s')


if __name__ == "__main__":
    main()
