from typing import List
from narraint.analysis.documentranking.ranker import AbstractDocumentRanker, AnalyzedQuery, AnalyzedNarrativeDocument
import pandas as pd
import pyterrier as pt
if not pt.started():
    pt.init()
import onir_pt
#pip install --upgrade git+https://github.com/Georgetown-IR-Lab/OpenNIR


class IndexRanker(AbstractDocumentRanker):

    def __init__(self, name):
        super().__init__(self, name)

    @staticmethod
    def index_documents(narrative_documents: List[AnalyzedNarrativeDocument]):
        df = pd.concat([pd.DataFrame([[str(d.document.id), d.get_text()]],
                                     columns=["docno", "text"]) for d in narrative_documents], ignore_index=True)
        indexer = pt.DFIndexer(index_path='', type=pt.index.IndexingType.MEMORY)
        index_ref = indexer.index(df["text"], df)
        index = pt.IndexFactory.of(index_ref)
        return index

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        pass


class BM25Ranker(IndexRanker):

    def __init__(self):
        super().__init__(name="BM25Ranker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        index = super().index_documents(narrative_documents)
        br = pt.BatchRetrieve(index, wmodel="BM25")
        return list(br.search(query.keyword_query)[['docno', 'score']].to_records(index=False))


class TFIDFRanker(IndexRanker):

    def __init__(self):
        super().__init__(name="TFIDFRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        index = super().index_documents(narrative_documents)
        br = pt.BatchRetrieve(index, wmodel="TF_IDF")
        return list(br.search(query.keyword_query)[['docno', 'score']].to_records(index=False))


class OpenNIRRanker(IndexRanker):

    def __init__(self):
        super().__init__(name="OpenNIRRanker")

    def rank_documents(self, query: AnalyzedQuery, narrative_documents: List[AnalyzedNarrativeDocument]):
        index = super().index_documents(narrative_documents)
        br = pt.BatchRetrieve(index)
        # https://arxiv.org/abs/2010.05987
        vbert = onir_pt.reranker.from_checkpoint('https://macavaney.us/scibert-medmarco.tar.gz', text_field='text',
                                                 expected_md5="854966d0b61543ffffa44cea627ab63b")
        pipeline = br >> pt.text.get_text(index, 'text') >> vbert
        return list(pipeline.search(query.keyword_query)[['docno', 'score']].to_records(index=False))
