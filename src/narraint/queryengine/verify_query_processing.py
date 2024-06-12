import logging

from kgextractiontoolbox.progress import Progress
from narraint.frontend.ui.views import View
from narraint.queryengine.engine import QueryEngine
import requests

inputs = [
    '"post-acute COVID-19 syndrome" associated Disease',
    'Covid19 associated Target',
    'Simvastatin induces Rhabdomyolysis',
    'Metformin inhibits mtor',
    'Metformin treats "Diabetes Mellitus" _AND_ Metformin associated human',
]

data_source = 'PubMed'


def main():
    j = 0
    p = Progress(text='Query processing tests')
    p.start_time()

    for i in inputs:
        # Calculate the local service result count
        graph_query, _ = View().translation.convert_query_text_to_fact_patterns(i)
        results = QueryEngine.process_query_with_expansion(graph_query=graph_query, document_collection_filter={'PubMed'})

        # Retrieve the live service query result
        res = requests.get(f'http://narrative.pubpharm.de/query',
                           params={'query': i, 'data_source': data_source})
        if not 200 <= res.status_code < 300:
            continue

        # Calculate the live service result count
        data = res.json()
        count = data['results']['s']

        # Check that the local query processing retrieves as many results as the live service.
        if len(results) >= count:
            j += 1
    logging.info(f'{j} of {len(inputs)} tests passed')
    p.done()


if __name__ == "__main__":
    main()
