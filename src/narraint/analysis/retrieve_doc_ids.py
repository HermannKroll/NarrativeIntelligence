import random

from narraint.frontend.ui.views import convert_query_text_to_fact_patterns, View

q1 = "Simvastatin decreases Neoplasms. Simvastatin effects Species:9606"
collection = "PMC"
sample_size = 10

query_fact_patterns, query_trans = convert_query_text_to_fact_patterns(q1)
print(q1)
print(query_fact_patterns)

query_results = View.instance().query_engine.query_with_graph_query(query_fact_patterns, q1, collection)
doc_ids = set()
i = 0
for q_r in query_results:
    i += 1
    doc_ids.add(q_r.document_id)

print(i)
print(len(doc_ids))
print(doc_ids)
sample = random.sample(doc_ids, sample_size)
print("=" * 60)
print("=" * 60)
print("sample")
for s in sample:
    print(s)

print("=" * 60)
print("=" * 60)
