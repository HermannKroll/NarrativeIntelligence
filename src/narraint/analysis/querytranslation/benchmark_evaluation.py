import json
import logging
import os
import csv
from xml.etree import ElementTree
from abc import abstractmethod, ABC
import pytrec_eval
from collections import defaultdict

from narraint.analysis.querytranslation.data_graph import DataGraph
from narraint.analysis.querytranslation.ranker import EntityFrequencyBasedRanker
from narraint.analysis.querytranslation.translation import QueryTranslationToGraph, SchemaGraph

ROOT_DIR = '/home/kroll/jupyter/JCDL2023/'
RESOURCES_DIR = os.path.join(ROOT_DIR, 'resources')

# BENCHMARK DATA
TREC_COVID_DIR = os.path.join(RESOURCES_DIR, 'trec_covid')
PRECISION_MED_DIR = os.path.join(RESOURCES_DIR, 'precision_medicine')
TREC_GENOMICS_DIR = os.path.join(RESOURCES_DIR, 'trec_genomics')

BENCHMARKS = ['trec-genomics',
              'precision-med']  # ['trec-covid-abstract', 'precision-med', 'trec-genomics', 'all'] # 'trec-covid-fulltext',

translation = QueryTranslationToGraph(data_graph=DataGraph(), schema_graph=SchemaGraph())


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
        return str(self.query)


class PrecisionMedTopic(Topic):
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


class Benchmark(ABC):
    def __init__(self, path, topics_file, qrel_file):
        self.path = path
        self.topics: list[Topic] = list()
        self.qrels: dict = dict()
        self.topics_file = topics_file
        self.qrel_file = qrel_file
        self.relevant_document_ids = set()
        self.topic2doc_ids = defaultdict(set)

    @abstractmethod
    def parse_topics(self):
        pass

    def parse_qrels(self):
        path = os.path.join(self.path, self.qrel_file)
        with open(path) as file:
            for line in file.readlines():
                topic_num, _, doc_id, judgement = line.split()
                self.relevant_document_ids.add(str(doc_id))
                self.topic2doc_ids[str(topic_num)].add(str(doc_id))
                if topic_num not in self.qrels:
                    self.qrels[topic_num] = {doc_id: int(judgement)}
                else:
                    self.qrels[topic_num][doc_id] = int(judgement)

        print(
            f'Found {len(self.relevant_document_ids.intersection(document_ids_in_db_title))} with title out of {len(self.relevant_document_ids)} in DB')
        print(
            f'Found {len(self.relevant_document_ids.intersection(document_ids_in_db_abstract))} with abstract out of {len(self.relevant_document_ids)} in DB')

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

    def evaluate(self, measures) -> dict:
        result = dict()
        evaluator = pytrec_eval.RelevanceEvaluator(self.qrels, measures)

        print(f'Benchmark has {len(self.relevant_document_ids)} documents')
        # TODO: service request with appropriate data (check for each bm the best way to send data)
        for idx, topic in enumerate(self.topics):
            # skip not relevant topics
            if str(topic.number) not in self.qrels:
                print(f'Topic {topic.number} not relevant for benchmark')
                continue

            topic_res = list()
            query_str = topic.get_test_data()
            # Todo: hack
            # query_str = query_str.replace('coronavirus', 'covid-19')

            print(f'\nTopic {str(topic.number)}: {query_str} \n')
            queries = translation.translate_keyword_query(query_str, verbose=False)
            # Get the most relevant query
            q = EntityFrequencyBasedRanker.rank_queries(queries)[0]

            q_document_ids = {str(d) for d in
                              translation.data_graph.compute_query(q)}  # convert doc ids to strings here
            found_in_dg = len(q_document_ids)
            # Restrict document ids to benchmark relevant ids
            q_document_ids = q_document_ids.intersection(self.relevant_document_ids)

            doc_ids_relevant_for_topic = self.topic2doc_ids[str(topic.number)]
            print(
                f'{len(q_document_ids)} / {len(doc_ids_relevant_for_topic)} relevant document ids for query: {q} (found {found_in_dg} matches in DB) ')
            topic_res = {d: 2.0 for d in q_document_ids}

            result[str(topic.number)] = topic_res  # self._normalize_data(topic_res)
            print('\nResults:')
            print(evaluator.evaluate({str(topic.number): topic_res}))

            RELAX_QUERIES = True
            if RELAX_QUERIES:
                q_rel_document_ids = {str(d) for d in translation.data_graph.compute_query(q)}
                rel_queries = list(Query.relax_query(q, delete_operations=1))
                for r_q in rel_queries:
                    q_rel_document_ids.update({str(d) for d in translation.data_graph.compute_query(r_q)})

                # Restrict document ids to benchmark relevant ids
                q_rel_document_ids = q_rel_document_ids.intersection(self.relevant_document_ids)
                print(f'\nComputed {len(rel_queries)} relaxed queries resulting in:')
                topic_res_relaxed = {d: 2.0 for d in q_rel_document_ids}
                print(evaluator.evaluate({str(topic.number): topic_res_relaxed}))
            # print(result[str(topic.number)])

        # TODO normalize received data
        # TODO evaluate and return
        # scores = evaluator.evaluate(result)
        # for q in scores:
        #    print(f'{q} => {scores[q]}\n\n')
        return evaluator.evaluate(result)  # result)

    def __str__(self):
        return f'[{self.__class__.__name__}] topics({len(self.topics)}) qrels({len(self.qrels.keys())})'


class TRECGenomicsBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file):
        super().__init__(TREC_GENOMICS_DIR, topics_file, qrel_file)

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
                self.topic2doc_ids[str(topic_num)].add(str(pubmed_id))
                if topic_num not in self.qrels:
                    self.qrels[topic_num] = {pubmed_id: judge_dict[judgement]}
                else:
                    self.qrels[topic_num][pubmed_id] = judge_dict[judgement]

        print(
            f'Found {len(self.relevant_document_ids.intersection(document_ids_in_db_title))} with title out of {len(self.relevant_document_ids)} in DB')
        print(
            f'Found {len(self.relevant_document_ids.intersection(document_ids_in_db_abstract))} with abstract out of {len(self.relevant_document_ids)} in DB')


class TRECCovidBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file, use_fulltext=False):
        super().__init__(TREC_COVID_DIR, topics_file, qrel_file)
        self.use_fulltext = use_fulltext

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


class PrecisionMedBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file):
        super().__init__(PRECISION_MED_DIR, topics_file, qrel_file)

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

            self.topics.append(PrecisionMedTopic(number, disease, gene, treatment))


class BenchmarkRunner:
    def __init__(self, bm_list: list[str], file, measures):
        self.benchmarks: list[Benchmark] = list()
        self.file = file
        self.measures = measures

        self.create_benchmarks(bm_list)

    def create_benchmarks(self, bm_list: list[str]):
        if bm_list[0] == 'all':
            bm_list = list(BENCHMARKS)
        if 'trec-covid-abstract' in bm_list:
            self.benchmarks.append(TRECCovidBenchmark('topics-rnd5.xml', 'qrels-covid_d5_j4.5-5.txt'))
        if 'trec-covid-fulltext' in bm_list:
            self.benchmarks.append(TRECCovidBenchmark('topics-rnd5.xml', 'qrels-covid_d5_j4.5-5.txt', True))
        if 'precision-med' in bm_list:
            self.benchmarks.append(PrecisionMedBenchmark('topics2020.xml', 'qrels-reduced-phase1-treceval-2020.txt'))
        if 'trec-genomics' in bm_list:
            self.benchmarks.append(TRECGenomicsBenchmark('2007topics.txt', 'trecgen2007.all.judgments.tsv.txt'))

    def run(self):
        print("Evaluation".center(50, '='))
        print(f'measures {self.measures}')
        print(f'Running benchmarks: {self.benchmarks}')
        result = list()
        for bm in self.benchmarks:
            bm.initialize()
            print(bm)
            result.append(bm.evaluate(self.measures))

            if self.file is not None:
                filename = '{}_{}{}.json' \
                    .format(self.file, bm.__class__.__name__.lower(),
                            "_fulltext" if hasattr(bm, "use_fulltext") and bm.use_fulltext else "")
                with open(filename, 'w') as file:
                    file.write(json.dumps(result.pop()))

        if self.file is None:
            print("Results".center(50, '='))
            [print(f'{x}') for x in result]


metrics = {'map',
           'ndcg',
           'P',
           'recall'
           }

# metrics = pytrec_eval.supported_measures
BenchmarkRunner(["all"], "test_run.txt", metrics).run()
