import argparse
import json
from pathlib import Path

from kgextractiontoolbox.progress import Progress


def main():
    parser = argparse.ArgumentParser("count wikipedia articles")
    parser.add_argument("rootdir")
    args = parser.parse_args()
    rootdir = Path(args.rootdir)

    count = 0
    paths = list(rootdir.rglob("wiki_*"))
    total_docs = len(paths)

    prog = Progress(total_docs, text="Counting wikipedia articles")
    prog.start_time()
    for n, p in enumerate(paths):
        prog.print_progress(n)
        with open(p) as f:
            for line in f:
                doc = json.loads(line)
                if doc["text"]:
                    count += 1
    prog.done()
    print(f"Found {count} articles with text.")

if __name__ == '__main__':
    main()