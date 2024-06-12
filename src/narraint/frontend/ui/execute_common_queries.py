import logging

from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.frontend.ui.search_cache import SearchCache
from narraint.queryengine.aggregation.substitution_tree import ResultTreeAggregationBySubstitution
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
    'Covid19 associated Pfizer Covid 19 Vaccine _AND_ Human associated Disease',
    "post-acute COVID-19 syndrome associated Disease",
    "Drug treats post-acute COVID-19 syndrome"
]

FREQUENT_CONCEPTS = [
    "covid 19",
    "long covid",
    "Chronic Fatigue Syndrome",

    "Acetylsalicylic acid",
    "Aflibercept",
    "Ambazone",
    "Amlodipine",
    "amphotericin",
    "amsacrine",
    "Aspirin",
    "Baloxavir marboxil",
    "baricitinib",
    "Bisoprolol",
    "Cannabis",
    "Carvedilol",
    "Crataegus",
    "daratumumab",
    "diabetes mellitus",
    "Difelikefalin",
    "Digitoxin",
    "Disintegrin",
    "Docetaxel",
    "Elacestrant",
    "Enalapril",
    "Erlotinib",
    "Ertugliflozin",
    "Escitalopram",
    "Etoricoxib",
    "etrasimod",
    "Exenatide",
    "hay fever",
    "Hypericin",
    "hypericum perforatum",
    "Ibuprofen",
    "jacaranone",
    "Ketamine",
    "Lasmiditan",
    "Leprosy",
    "Lercanidipin",
    "Meprobamate",
    "Metamizol",
    "Metformin",
    "Mirtazapine",
    "Nebivolol",
    "Omega 3 fatty acids",
    "Omeprazole",
    "Palmitoylethanolamid",
    "Psilocin",
    "Quinapril",
    "Rivaroxaban",
    "Selinexor",
    "Sertraline",
    "sitagliptin",
    "Sumatriptan",
    "Ticagrelor",
    "Valsartan",
    "Vemurafenib",
    "Venlafaxine",
    "budesonide",
    "paclitaxel",
    "coffeine",
    "simvastatin",
    "upadacitinib"
]

DRUG_OVERVIEW_QUERY_TEMPLATES = [
    "XXX treats Disease",
    "XXX administered DosageForm",
    "XXX interacts Target",
    "XXX method LabMethod",
    "XXX associated ?X(Species)",
    "XXX associated ?X(Drug)",
    "XXX interacts Drug",
    "XXX induces Disease",
    "XXX associated ?X(Tissue)",
    "Drug associated XXX",
    "Disease associated XXX",
    "Gene associated XXX"
]


def execute_common_queries():
    cache = SearchCache()
    translation = QueryTranslation()
    for q in COMMON_QUERIES:
        logging.info('Caching Query: {}'.format(q))
        graph_query, query_trans_string = translation.convert_query_text_to_fact_patterns(q)
        for collection in ['PubMed', 'LitCovid', "LongCovid", "ZBMed"]:

            results = QueryEngine.process_query_with_expansion(graph_query,
                                                               document_collection_filter={collection})
            logging.info('Write results to cache...')
            try:
                cache.add_result_to_cache(collection, graph_query, results)
            except Exception:
                logging.error('Cannot store query result to cache...')


def execute_frequent_drug_overviews():
    cache = SearchCache()
    translation = QueryTranslation()
    aggregation_strategy = "overview"
    collection = "PubMed"

    for drug in FREQUENT_CONCEPTS:
        for qt in DRUG_OVERVIEW_QUERY_TEMPLATES:
            query_str = qt.replace("XXX", drug.strip())
            logging.info('Caching Query: {}'.format(query_str))
            graph_query, query_trans_string = translation.convert_query_text_to_fact_patterns(query_str)

            results = QueryEngine.process_query_with_expansion(graph_query,
                                                               document_collection_filter={collection},
                                                               load_document_metadata=False)

            # next get the aggregation by var names
            substitution_aggregation = ResultTreeAggregationBySubstitution()
            results_ranked, is_aggregate = substitution_aggregation.rank_results(results, freq_sort_desc=True)

            # generate a list of [(ent_id, ent_name, doc_count), ...]
            sub_count_list = list()
            # go through all aggregated results
            for aggregate in results_ranked.results:
                var2sub = aggregate.var2substitution
                # get the first substitution
                var_name, sub = next(iter(var2sub.items()))
                sub_count_list.append(dict(id=sub.entity_id,
                                           name=sub.entity_name,
                                           count=aggregate.get_result_size()))

            cache.add_result_to_cache(collection, graph_query,
                                      sub_count_list,
                                      aggregation_name=aggregation_strategy)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    execute_common_queries()
    execute_frequent_drug_overviews()


if __name__ == "__main__":
    main()
