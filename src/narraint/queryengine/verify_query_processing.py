from kgextractiontoolbox.progress import Progress
from narraint.frontend.ui.views import View
from narraint.queryengine.engine import QueryEngine


inputs = [
    ["\"post-acute COVID-19 syndrome\" associated Disease", 1424],
    ["Covid19 associated Target", 18039],
    ["Simvastatin induces Rhabdomyolysis", 82],
    ["Metformin inhibits mtor", 282],
    ["Metformin treats \"Diabetes Mellitus\" _AND_ Metformin associated human", 4055]
]


def main():
    # DONE It should run some example queries and check that at least a certain number of documents is contained
    #  (DB might be updated, and so, we should to a greater than comparison to consider updates).

    # DONE For example, select 5 example queries and then process the query, count the number of distinct documents
    #  and compare it the actual number of publications in our Live service www.narrative.pubpharm.de

    # TODO FOR NOW: store queries as an array with the corresponding result count. Evaluate the query and compare the
    #  result with the previously stored amount.
    #  Next step is to retrieve the live count for each query from the live database to be more flexible.

    # progress = 0
    # p = Progress(total=len(inputs))
    # p.start_time()

    for i in inputs:
        graph_query, _ = View.instance().translation.convert_query_text_to_fact_patterns(i[0])

        # TODO test for more than PubMed collection
        results = QueryEngine.process_query_with_expansion(graph_query=graph_query, document_collection_filter={"PubMed"})

        assert len(results) >= i[1]

        # p.print_progress(progress + 1)
        # progress += 1

    # p.done()


if __name__ == "__main__":
    main()
