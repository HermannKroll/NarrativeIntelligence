import csv
import json
import os
import re
from abc import abstractmethod, ABC
from collections import defaultdict
from datetime import datetime
from xml.etree import ElementTree

import pytrec_eval
from tqdm import tqdm

from kgextractiontoolbox.backend.models import DocumentTranslation
from narraint.analysis.documentranking.ranker import AnalyzedQuery, \
    ConceptDocumentRanker, ConceptFrequencyDocumentRanker, StatementPartialOverlapDocumentRanker, \
    StatementOverlapDocumentRanker, DocumentRetriever, EqualDocumentRanker

from narraint.analysis.querytranslation.data_graph import DataGraph
from narraint.backend.database import SessionExtended

pubmed_graph = DataGraph(document_collection="PubMed")

session = SessionExtended.get()
covid19_abstract_graph = DataGraph(document_collection="TREC_COVID_ABSTRACTS")
covid19_abstract_doc2source = DocumentTranslation.get_document_id_2_source_id_mapping(session, "TREC_COVID_ABSTRACTS")
print(f'Found {len(covid19_abstract_doc2source)} mappings for TREC_COVID_ABSTRACTS')
covid19_fulltext_graph = DataGraph(document_collection="TREC_COVID_FULLTEXTS")
covid19_fulltext_doc2source = DocumentTranslation.get_document_id_2_source_id_mapping(session, "TREC_COVID_FULLTEXTS")
print(f'Found {len(covid19_fulltext_doc2source)} mappings for TREC_COVID_FULLTEXTS')

ROOT_DIR = '/home/kroll/jupyter/JCDL2023/'
RESOURCES_DIR = os.path.join(ROOT_DIR, 'resources')

# BENCHMARK DATA
TREC_COVID_DIR = os.path.join(RESOURCES_DIR, 'trec_covid')
PRECISION_MED_DIR = os.path.join(RESOURCES_DIR, 'precision_medicine')
TREC_GENOMICS_DIR = os.path.join(RESOURCES_DIR, 'trec_genomics')
TRIP_CLICK_DIR = os.path.join(RESOURCES_DIR, 'trip_click')
TRIP_JUDGE_DIR = os.path.join(RESOURCES_DIR, 'trip_judge')

USED_RANKING_STRATEGIES = [EqualDocumentRanker(),
                           ConceptDocumentRanker(), ConceptFrequencyDocumentRanker(),
                           StatementPartialOverlapDocumentRanker(), StatementOverlapDocumentRanker()]

document_retriever = DocumentRetriever()
print('Finished')

BENCHMARKS = ['prec-med-2020']


# BENCHMARKS = [ 'prec-med-2020']  # , 'trec-genomics'] #['trec-covid-abstract', 'prec-med-2020', 'trec-genomics', 'all'] # 'trec-covid-fulltext',


class Topic(ABC):
    @abstractmethod
    def __init__(self, number):
        self.number = int(number)

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def get_test_data(self) -> str:
        """
        :return: keywords joined as string, separated by a space
        """
        pass


class TRECGenomicsTopic(Topic):
    def __init__(self, number, question):
        super().__init__(number)
        self.question = question

    def __str__(self):
        return f'[{self.number:02d}] question: {self.question}\n'

    def get_test_data(self) -> str:
        return str(self.question)

    def get_result_data(self) -> str:
        pass


class TRECCovidTopic(Topic):
    def __init__(self, number, query, question, narrative):
        super().__init__(number)
        self.query = query
        self.question = question
        self.narrative = narrative

    def __str__(self):
        return f'[{self.number:02d}] query: {self.query}; question: {self.question}; narrative: {self.narrative}\n'

    def get_test_data(self) -> str:
        query_str = str(self.query)
        query_str = query_str.replace('coronavirus', 'covid-19')
        return query_str


class PrecMed2020Topic(Topic):
    def __init__(self, number, disease, gene, treatment):
        super().__init__(number)
        self.disease = disease
        self.gene = gene
        self.treatment = treatment

    def __str__(self):
        return f'[{self.number:02d}] disease: {self.disease}; gene: {self.gene}; treatment: {self.treatment}'

    def get_test_data(self) -> str:
        return f'{self.disease} {self.gene} {self.treatment}'

    def get_result_data(self) -> str:
        # TODO what is the result? Nothing given?
        pass


class TripClickTopic(Topic):
    def __init__(self, number, keywords):
        super().__init__(number)
        self.keywords = keywords

    def __str__(self):
        return f'[{self.number}:02d] keywords: {self.keywords}'

    def get_test_data(self) -> str:
        return self.keywords


class Benchmark(ABC):
    def __init__(self, path, topics_file, qrel_file, name):
        self.path = path
        self.topics: list[Topic] = list()
        self.qrels: dict = dict()
        self.topics_file = topics_file
        self.qrel_file = qrel_file
        self.relevant_document_ids = set()
        self.topic2doc_ids = defaultdict(set)
        self.name = name
        self.evaluation_graph = pubmed_graph

    @abstractmethod
    def parse_topics(self):
        pass

    def translate_document_id(self, document_id):
        return str(document_id)

    def parse_qrels(self):
        path = os.path.join(self.path, self.qrel_file)
        with open(path) as file:
            for line in file.readlines():
                topic_num, _, doc_id, judgement = line.split()
                doc_id = str(doc_id)
                judgement = int(judgement)

                self.relevant_document_ids.add(doc_id)

                if topic_num not in self.qrels:
                    self.qrels[topic_num] = {}
                    self.topic2doc_ids[str(topic_num)] = set()

                self.qrels[topic_num][doc_id] = judgement
                if judgement >= 1:
                    self.topic2doc_ids[str(topic_num)].add(doc_id)

    def initialize(self):
        self.parse_topics()
        self.parse_qrels()

    @staticmethod
    def _normalize_data(documents):
        """
        Return list of documents having normalized [0,2] result values. Therefore, the list has to
        be sorted in descending order by the importance of each document.
        """
        topic_res = {}
        num_docs = i = len(documents)
        for doc in range(len(documents)):
            topic_res[documents[doc]] = i / num_docs * 2  # normalize to [0;2]
            i -= 1
        return topic_res

    def evaluate(self, measures, verbose=True) -> [dict]:
        print(f'The evaluation graph will use the document collection: {self.evaluation_graph.document_collection}')
        print(f'{len(self.relevant_document_ids)} documents are included in this benchmark')
        evaluator = pytrec_eval.RelevanceEvaluator(self.qrels, measures)

        if verbose: print(f'Benchmark has {len(self.relevant_document_ids)} documents')

        bm_results = {}
        for min_keywords in range(0, 1):
            print(f'Forcing queries to have: {min_keywords} keywords')
            bm_results[min_keywords] = {}
            enum_topics = enumerate(sorted([t for t in self.topics if str(t.number) in self.qrels],
                                           key=lambda x: int(x.number)))
            if not verbose:
                enum_topics = tqdm(enum_topics, total=len(self.qrels))
            for idx, topic in enum_topics:
                query_str = topic.get_test_data()
                no_keywords = len(query_str.strip().split(' '))

                # skip all topics with to less keywords
                if no_keywords < min_keywords:
                    continue

                # Todo: hack
                # query_str = query_str.replace('coronavirus', 'covid-19')

                if verbose:
                    print('--' * 60)
                    print(f'Topic {str(topic.number)}: {query_str} \n')

                analyzed_query = AnalyzedQuery(keyword_query=query_str)
                document_ids = {self.translate_document_id(d)
                                for d in document_retriever.retrieve_document_ids_for_query(analyzed_query,
                                                                                            self.evaluation_graph)}
                # Restrict document ids to benchmark relevant ids
                benchmark_document_ids = document_ids.intersection(self.relevant_document_ids)
                # Next geht the narrative documents
                narrative_documents = document_retriever.retrieve_narrative_documents(benchmark_document_ids,
                                                                                      self.evaluation_graph.document_collection)

                for ranker in USED_RANKING_STRATEGIES:
                    before = datetime.now()
                    ranked_document_ids = ranker.rank_documents(analyzed_query, narrative_documents)
                    after = datetime.now()
                    doc_ids_relevant_for_topic = self.topic2doc_ids[str(topic.number)]
                    topic_res = {str(d): sco for d, sco in Benchmark._normalize_data(ranked_document_ids).items()}

                    result_dict = {}
                    result_dict['ranking_time'] = str((after - before))
                    result_dict['metrics'] = evaluator.evaluate({str(topic.number): topic_res})[str(topic.number)]
                    result_dict["doc_ids_retrieved"] = len(benchmark_document_ids)
                    result_dict["doc_ids_relevant"] = len(doc_ids_relevant_for_topic)
                    result_dict["query"] = str(analyzed_query.keywords)
                    result_dict["query_org"] = query_str
                    if verbose:
                        print(result_dict)

                    if ranker.name not in bm_results[min_keywords]:
                        bm_results[min_keywords][ranker.name] = {}
                    bm_results[min_keywords][ranker.name][topic.number] = result_dict

        # TODO normalize received data
        # TODO evaluate and return
        return bm_results

    def __str__(self):
        return f'[{self.__class__.__name__}] topics({len(self.topics)}) qrels({len(self.qrels.keys())})'

    def analyze(self, path):
        pass


class TRECGenomicsBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file):
        super().__init__(TREC_GENOMICS_DIR, topics_file, qrel_file, name="TREC_Genomics")

    def parse_topics(self):
        path = os.path.join(self.path, self.topics_file)
        with open(path) as file:
            lines = file.readlines()

        for line in lines:
            line = line.split('>')
            number = line[0].split('<')[1]

            self.topics.append(TRECGenomicsTopic(number, line[1]))

    def parse_qrels(self):
        judge_dict = {'RELEVANT': 2, 'NOT_RELEVANT': 0}
        path = os.path.join(self.path, self.qrel_file)
        with open(path) as file:
            qrel_csv = csv.reader(file, delimiter='\t')

            for line in qrel_csv:
                topic_num, pubmed_id, _, _, judgement = line
                self.relevant_document_ids.add(str(pubmed_id))
                if judgement == 'RELEVANT':
                    self.topic2doc_ids[str(topic_num)].add(str(pubmed_id))
                if topic_num not in self.qrels:
                    self.qrels[topic_num] = {pubmed_id: judge_dict[judgement]}
                else:
                    self.qrels[topic_num][pubmed_id] = judge_dict[judgement]


class TRECCovidBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file, use_fulltext=False):
        name = "TREC_Covid"
        self.use_fulltext = use_fulltext
        if use_fulltext:
            local_evaluation_graph = covid19_fulltext_graph
            name = name + "_fulltext"
        else:
            local_evaluation_graph = covid19_abstract_graph

        super().__init__(TREC_COVID_DIR, topics_file, qrel_file, name=name)
        self.use_fulltext = use_fulltext
        self.evaluation_graph = local_evaluation_graph

    def translate_document_id(self, document_id):
        if self.use_fulltext:
            return covid19_fulltext_doc2source[int(document_id)]
        else:
            return covid19_abstract_doc2source[int(document_id)]

    def parse_topics(self):
        path = os.path.join(self.path, self.topics_file)
        with open(path) as file:
            root = ElementTree.parse(file).getroot()

        if root is None:
            return

        for topic in root.findall('topic'):
            number = topic.get('number')
            query = topic.find('query').text.strip()
            question = topic.find('question').text.strip()
            narrative = topic.find('narrative').text.strip()

            self.topics.append(TRECCovidTopic(number, query, question, narrative))

    def __str__(self):
        return f'{super().__str__()} using {"fulltext" if self.use_fulltext else "abstracts"}'


class PrecMed2020Benchmark(Benchmark):
    def __init__(self, topics_file, qrel_file):
        super().__init__(PRECISION_MED_DIR, topics_file, qrel_file, name="PM2020")

    def parse_topics(self):
        path = os.path.join(self.path, self.topics_file)
        with open(path) as file:
            root = ElementTree.parse(file).getroot()

        if root is None:
            return

        for topic in root.findall('topic'):
            number = topic.get('number')
            disease = topic.find('disease').text.strip()
            gene = topic.find('gene').text.strip()
            treatment = topic.find('treatment').text.strip()

            self.topics.append(PrecMed2020Topic(number, disease, gene, treatment))


class TripClickBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file, path=TRIP_CLICK_DIR, name="TripClick"):
        super().__init__(path, topics_file, qrel_file, name=name)

    def parse_topics(self):
        top_pattern = re.compile(r"(?s)<top>\n*(.*?)\n*</top>")

        for topics_file in self.topics_file:
            path = os.path.join(self.path, topics_file)
            with open(path) as file:
                # structure
                # <top>
                #   <num> Number: 8
                #   <title> acute appendicitis
                #   <desc> Descrption:
                #   <narr> Narrative:
                # </top>

                # ignoring "desc"- and "narr"-tags (they are most likely empty)
                topics_raw = re.findall(top_pattern, file.read())
                topics_cleaned = [[int(t[0].split(':')[-1].strip()), t[1].split('> ')[-1].strip()]
                                  for t in [x.split('\n') for x in topics_raw]]
                self.topics.extend([TripClickTopic(*t) for t in topics_cleaned])

    def parse_qrels(self):
        for qrel_file in self.qrel_file:
            path = os.path.join(self.path, qrel_file)
            with open(path) as file:
                for line in file.readlines():
                    topic_num, _, doc_id, judgement = line.split()
                    doc_id = str(doc_id)

                    self.relevant_document_ids.add(doc_id)

                    if topic_num not in self.qrels:
                        self.qrels[topic_num] = {}
                    self.qrels[topic_num][doc_id] = int(judgement)


class TripJudgeBenchmark(TripClickBenchmark):
    def __init__(self, topics_files, qrel_files):
        super().__init__(topics_file=topics_files, qrel_file=qrel_files, path=TRIP_JUDGE_DIR, name="TripJudge")


class BenchmarkRunner:
    def __init__(self, bm_list: list[str], path, measures):
        self.benchmarks: list[Benchmark] = list()
        self.path = path
        self.measures = measures

        self.create_benchmarks(bm_list)

    def create_benchmarks(self, bm_list: list[str]):
        if bm_list[0] == 'all':
            bm_list = list(BENCHMARKS)
        if 'trec-covid-abstract' in bm_list:
            self.benchmarks.append(TRECCovidBenchmark('topics-rnd5.xml', 'qrels-covid_d5_j4.5-5.txt'))
        if 'trec-covid-fulltext' in bm_list:
            self.benchmarks.append(TRECCovidBenchmark('topics-rnd5.xml', 'qrels-covid_d5_j4.5-5.txt', True))
        if 'prec-med-2020' in bm_list:
            self.benchmarks.append(PrecMed2020Benchmark('topics2020.xml', 'qrels-reduced-phase1-treceval-2020.txt'))
        if 'trec-genomics' in bm_list:
            self.benchmarks.append(TRECGenomicsBenchmark('2007topics.txt', 'trecgen2007.all.judgments.tsv.txt'))
        if 'trip-click' in bm_list:
            self.benchmarks.append(TripClickBenchmark(['topics.head.test.txt', 'topics.head.val.txt'],
                                                      ['qrels.raw.head.test.txt', 'qrels.raw.head.val.txt']))
        if 'trip-judge' in bm_list:
            self.benchmarks.append(TripJudgeBenchmark(['topics.head.test.txt'], ['qrels_2class.txt']))

    @staticmethod
    def add_summary_to_metric_dict(bm_result):
        # compute summary per ranking strategy
        for min_keyword in bm_result:
            for ranking in bm_result[min_keyword]:
                summary_dict = {"topics_answered": [], "topics_not_answered": [], "sum_all": {}, "sum_answered": {}}
                answered, not_answered = 0, 0
                for topic, topic_dict in bm_result[min_keyword][ranking].items():
                    if topic_dict['doc_ids_retrieved'] > 0:
                        summary_dict["topics_answered"].append(topic_dict['query_org'])
                        answered += 1
                    else:
                        summary_dict["topics_not_answered"].append(topic_dict['query_org'])
                        not_answered += 1

                    for metric in topic_dict['metrics']:
                        if metric not in summary_dict["sum_all"]:
                            summary_dict["sum_all"][metric] = topic_dict['metrics'][metric]
                        else:
                            summary_dict["sum_all"][metric] += topic_dict['metrics'][metric]

                    if topic_dict['doc_ids_retrieved'] > 0:
                        for metric in topic_dict['metrics']:
                            if metric not in summary_dict['sum_answered']:
                                summary_dict['sum_answered'][metric] = topic_dict['metrics'][metric]
                            else:
                                summary_dict['sum_answered'][metric] += topic_dict['metrics'][metric]

                # Normalize result
                total_topics = len(bm_result[min_keyword][ranking])
                for metric in summary_dict["sum_all"]:
                    summary_dict["sum_all"][metric] /= total_topics

                # Normalize result
                for metric in summary_dict['sum_answered']:
                    summary_dict['sum_answered'][metric] /= answered

                bm_result[min_keyword][ranking]['summary'] = summary_dict
                bm_result[min_keyword][ranking]['summary']["answered"] = answered
                bm_result[min_keyword][ranking]['summary']["not answered"] = not_answered

    def run(self):
        print("Evaluation".center(50, '='))
        print(f'measures {self.measures}')
        print(f'Running benchmarks: {self.benchmarks}')
        result = list()
        for bm in self.benchmarks:
            bm.initialize()
            if self.path:
                bm.analyze(self.path)
            print(bm)
            bm_result = bm.evaluate(self.measures, verbose=False)
            BenchmarkRunner.add_summary_to_metric_dict(bm_result)

            if self.path is not None:
                benchmark_name = bm.name
                filename = f'retrieval_{benchmark_name}_results.json'
                filename = os.path.join(self.path, filename)

                print(f'Writing results to {filename}')
                with open(filename, 'w') as file:
                    file.write(json.dumps(bm_result))

        if self.path is None:
            print("Results".center(50, '='))
            [print(f'{x}') for x in result]


metrics = {'map',
           'ndcg',
           'P',
           'recall',
           'bpref'
           }

# metrics = pytrec_eval.supported_measures
BenchmarkRunner(["all"], "/home/kroll/jupyter/JCDL2023/", metrics).run()
