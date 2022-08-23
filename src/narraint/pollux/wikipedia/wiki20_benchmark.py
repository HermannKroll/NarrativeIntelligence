import json
from collections import defaultdict

BENCHMARK_FILE = "/home/kroll/NarrativeIntelligence/data/wiki20/wiki20m_test.txt"


def read_wiki20_benchmark():
    benchmark_entries = []
    entry_by_relation = defaultdict(list)
    skipped = 0
    with open(BENCHMARK_FILE, 'rt') as f:
        for line in f:
            data = json.loads(line)

            sentence_txt = ' '.join(data["token"])
            sentence_txt = sentence_txt.replace(' .', '.')
            sentence_txt = sentence_txt.replace(' ,', ',')

            subject_txt = data["h"]["name"]
            subject_id = data["h"]["id"]

            try:
                relation_txt = data["relation"]
                relation_id = data["r"]
            except KeyError:
                skipped += 1
                continue
                pass

            if relation_txt == "NA":
                skipped += 1
                continue

            object_txt = data["t"]["name"]
            object_id = data["t"]["id"]
            entry = (subject_txt, subject_id, relation_txt, relation_id, object_txt, object_id, sentence_txt)
            benchmark_entries.append(entry)
            entry_by_relation[(relation_id, relation_txt)].append(entry)

    print('a')


def main():
    # parser = argparse.ArgumentParser("Export documents from database with tags and predications")
    # parser.add_argument("-c", "--collection", help="Document collection")
    # parser.add_argument("-i", "--ids", help="Document ids", nargs="*")
    # parser.add_argument("output", help="output file")
    # args = parser.parse_args(args)

    read_wiki20_benchmark()


if __name__ == '__main__':
    main()
