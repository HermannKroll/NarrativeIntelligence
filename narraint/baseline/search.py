"""
Module is a wrapper classe for Lucene Core.

You can search for keywords in PubTator collections (single file). The indexing is transparent, i.e., the application
automatically creates a index.

This module uses pyLucene (Python module is named `lucene`) which is a wrapper around the Java library Lucene Core.
Code completion does not work.

For the Lucene Core documentation, see https://lucene.apache.org/core/8_1_1/core/overview-summary.html.

For examples, refer to:
- [Explanation of the search process](https://www.tutorialspoint.com/lucene/lucene_search_operation.htm)
- [Searching for documents](https://svn.apache.org/viewvc/lucene/pylucene/trunk/samples/SearchFiles.py?view=markup)
- [Indexing documents](https://svn.apache.org/viewvc/lucene/pylucene/trunk/samples/IndexFiles.py?view=markup)
"""
import hashlib
import os
from argparse import ArgumentParser
from datetime import datetime

import lucene
from java.nio.file import Paths
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import DirectoryReader, IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.search import IndexSearcher, TotalHits
from org.apache.lucene.store import SimpleFSDirectory

from narraint.config import TMP_DIR
from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import count_documents
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS

INDEX_DIR = os.path.join(TMP_DIR, "lucene")
N_RESULTS = 1000


def md5file(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def get_lucene_doc(pubtator_doc):
    ft_meta = FieldType()
    ft_meta.setStored(True)
    ft_meta.setTokenized(False)
    ft_meta.setIndexOptions(IndexOptions.DOCS_AND_FREQS)

    ft_content = FieldType()
    ft_content.setStored(False)
    ft_content.setTokenized(True)
    ft_content.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

    doc_id, doc_title, doc_content = CONTENT_ID_TIT_ABS.match(pubtator_doc).group(1, 2, 3)
    index_content = f"{doc_title} {doc_content}"

    doc = Document()
    doc.add(Field("id", doc_id, ft_meta))
    doc.add(Field("title", doc_title, ft_meta))
    doc.add(Field("contents", index_content, ft_content))
    return doc


def create_index(collection_file, index_dir):
    store = SimpleFSDirectory(Paths.get(index_dir))
    analyzer = StandardAnalyzer()
    analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)
    config = IndexWriterConfig(analyzer)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    writer = IndexWriter(store, config)

    total = count_documents(collection_file)
    start = datetime.now()
    for idx, doc in enumerate(read_pubtator_documents(collection_file)):
        lucene_doc = get_lucene_doc(doc)
        writer.addDocument(lucene_doc)
        print_progress_with_eta("Indexing", idx, total, start, 2)
    print("")

    writer.commit()
    writer.close()


def search(index_dir, query_str, top_n_results, out_file=None):
    directory = SimpleFSDirectory(Paths.get(index_dir))
    searcher = IndexSearcher(DirectoryReader.open(directory))
    analyzer = StandardAnalyzer()
    print("DEBUG: Using IR model", searcher.getSimilarity())

    query = QueryParser("contents", analyzer).parse(query_str)
    print(f"DEBUG: Searching '{query}' of type '{type(query)}'")
    top_docs = searcher.search(query, top_n_results)
    if top_docs.totalHits.relation == TotalHits.Relation.EQUAL_TO:
        print(f"INFO: Found exact {top_docs.totalHits.value} matches")
    else:
        print(f"INFO: Found at least {top_docs.totalHits.value} matches")

    # Print results
    f_out = None
    if out_file:
        f_out = open(out_file, "w")

    print("-" * 50)
    header = "No\tScore\tID\tTitle"
    if out_file:
        f_out.write(header + "\n")
    print(header)
    print("-" * 50)

    for idx, scoreDoc in enumerate(top_docs.scoreDocs):
        doc = searcher.doc(scoreDoc.doc)
        line = "{no}\t{score:.3f}\t{id}\t{title}".format(
            no=idx + 1,
            score=scoreDoc.score,
            id=doc.get("id"),
            title=doc.get("title"),
            # ex=searcher.explain(query, scoreDoc.doc),
        )
        if out_file:
            f_out.write(line + "\n")
        print(line)

    print("-" * 50)
    if out_file:
        f_out.close()
        print(f"Results written to: {out_file}")


def main():
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--index", help="Use existing index", metavar="INDEX_DIR", type=str)
    group.add_argument("-f", "--file", help="Use file (index will be created)", metavar="COLLECTION_FILE", type=str)
    parser.add_argument("-o", "--output", help="Write results to TSV", type=str, default=None)
    parser.add_argument("-n", help=f"Return top n results (default: {N_RESULTS})", type=str, default=N_RESULTS)
    parser.add_argument("query", help="Search query", type=str)
    args = parser.parse_args()

    lucene.initVM(
        vmargs=['-Djava.awt.headless=true']
    )
    print("DEBUG: Lucine", lucene.VERSION)

    # Create index
    if args.index:
        print(f"DEBUG: Using index {args.index}")
        index_dir = args.index
    else:
        if not os.path.exists(INDEX_DIR):
            os.mkdir(INDEX_DIR)
        md5sum = md5file(args.file)
        index_dir = os.path.join(INDEX_DIR, f"{args.file.split('/')[-1]}.{md5sum[:8]}")
        if os.path.exists(index_dir):
            print(f"DEBUG: Using index {index_dir}")
        else:
            print(f"DEBUG: Creating index {index_dir}")
            os.mkdir(index_dir)
            create_index(args.file, index_dir)

    # Search
    search(index_dir, args.query, args.n, args.output)


if __name__ == "__main__":
    main()
