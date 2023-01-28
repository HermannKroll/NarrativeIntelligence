import json


results = []
print("read input")
with open("docs.tsv") as f:
    for line in f:
        doc_id, content = line.split('\t')
        json_data = {"id": int(doc_id), "title": "", "abstract": content}
        results.append(json_data)

print("writing output")
with open("result.json", 'wt') as f_out:
    json.dump(results, f_out)

