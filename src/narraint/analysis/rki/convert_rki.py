import itertools
import json

from kgextractiontoolbox.document.document import TaggedDocument

docs = []
docs_raw = []
doc_ids = set()
pos, neg = 0, 0
with open('../../../../data/RKI/all.tsv', 'rt') as f:
    for line in itertools.islice(f, 1, None): # skip header
        doc_id, abstract, lc_class = line.split('\t')
        lc_class = int(lc_class)
        doc = TaggedDocument(id=int(doc_id), title="", abstract=abstract.strip())
        if lc_class == 0:
            doc.classification["class"] = "Non Long Covid"
            neg += 1
        else:
            doc.classification["class"] = "Long Covid"
            pos += 1
        docs_raw.append(doc)
        docs.append(doc.to_dict())
        doc_ids.add(int(doc_id))

print(f'found {len(doc_ids)} (pos: {pos} / neg: {neg})')
with open('../../../../data/RKI/all.json', 'wt') as f:
    json.dump(docs, f, indent=2)

long_covid_terms = 'post-covid-19 disease;post covid 19 disease;post-coronavirus disease (covid-19) syndrome;post-covid-19 symptom;post-acute COVID-19 syndrome;Chronic Coronavirus Disease Syndrome;Chronic COVID Syndrome;Long-haul Coronavirus Disease;Long-haul COVID;Post-Acute Sequelae of SARS-CoV-2 infection;Post-Acute Sequelae of Severe acute respiratory syndrome coronavirus 2;Post-Coronavirus Disease syndrome;Post-Coronavirus Disease-2019 syndrome;Post-COVID syndrome;Post-COVID-19 syndrome;chronic COVID syndrome;long COVID;long haul COVID;long hauler COVID;long-COVID;long-haul COVID;persistent COVID-19;post-acute COVID syndrome;post-acute COVID19 syndrome;post-acute sequelae of SARS-CoV-2 infection'
long_covid_terms = set(long_covid_terms.lower().replace('-', ' ').split(';'))
print(len(long_covid_terms))

docs_filtered = []
doc_ids_filtered = set()
pos, neg = 0, 0
for doc in docs_raw:
    has_lc = False
    for lc_term in long_covid_terms:
        if lc_term in  doc.abstract.replace('-', ' ').lower():
            has_lc = True
    if not has_lc:
        if doc.classification["class"] == "Long Covid":
            pos += 1
        else:
            neg += 1
        doc_ids_filtered.add(doc.id)
        docs_filtered.append(doc.to_dict())

print(f'filtered long covid documents {len(doc_ids_filtered)}')
print(f'found {len(doc_ids_filtered)} (pos: {pos} / neg: {neg})')
with open('../../../../data/RKI/all_no_long_covid_terms.json', 'wt') as f:
    json.dump(docs, f, indent=2)
with open('../../../../data/RKI/ids_without_direct_long_covid.txt', 'wt') as f:
    f.write('\n'.join([str(d_id) for d_id in doc_ids_filtered]))