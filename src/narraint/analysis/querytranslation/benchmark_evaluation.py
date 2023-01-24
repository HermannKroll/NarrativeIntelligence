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

from narraint.analysis.querytranslation.data_graph import DataGraph, Query
from narraint.analysis.querytranslation.enitytaggerjcdl import EntityTaggerJCDL
from narraint.analysis.querytranslation.ranker import EntityFrequencyBasedRanker, TermBasedRanker, EntityBasedRanker, \
    StatementBasedRanker, StatementFrequencyBasedRanker, MostSpecificQueryFirstRanker, \
    MostSpecificQueryFirstLimit1Ranker, MostSpecificQueryFirstLimit2Ranker, AssociatedRanker, MostSupportedQuery, \
    MostSpecificQueryWithResults, AssociatedRankerWithQueryResults, TreatsRanker
from narraint.analysis.querytranslation.translation import QueryTranslationToGraph, SchemaGraph

pubmed_graph = DataGraph(document_collection="PubMed")
translation = QueryTranslationToGraph(data_graph=pubmed_graph, schema_graph=SchemaGraph())

covid19_abstract_graph = DataGraph(document_collection="TREC_COVID_ABSTRACTS")
covid19_fulltext_graph = DataGraph(document_collection="TREC_COVID_FULLTEXTS")

ROOT_DIR = '/home/kroll/jupyter/JCDL2023/'
RESOURCES_DIR = os.path.join(ROOT_DIR, 'resources')

# BENCHMARK DATA
TREC_COVID_DIR = os.path.join(RESOURCES_DIR, 'trec_covid')
PRECISION_MED_DIR = os.path.join(RESOURCES_DIR, 'precision_medicine')
TREC_GENOMICS_DIR = os.path.join(RESOURCES_DIR, 'trec_genomics')
TRIP_CLICK_DIR = os.path.join(RESOURCES_DIR, 'trip_click')

# BENCHMARKS = ['precision-med']
BENCHMARKS = [
    'precision-med']  # , 'trec-genomics'] #['trec-covid-abstract', 'precision-med', 'trec-genomics', 'all'] # 'trec-covid-fulltext',
USED_RANKING_STRATEGIES = [TermBasedRanker, EntityBasedRanker, EntityFrequencyBasedRanker, StatementBasedRanker,
                           StatementFrequencyBasedRanker, MostSpecificQueryFirstRanker,
                           MostSpecificQueryFirstLimit1Ranker, MostSpecificQueryFirstLimit2Ranker, TreatsRanker,
                           AssociatedRanker,
                           MostSupportedQuery, MostSpecificQueryWithResults, AssociatedRankerWithQueryResults]
ALLOWED_DELETE_OPERATIONS = [1, 2]


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

    def parse_qrels(self):
        path = os.path.join(self.path, self.qrel_file)
        with open(path) as file:
            for line in file.readlines():
                topic_num, _, doc_id, judgement = line.split()
                doc_id = str(doc_id)

                self.relevant_document_ids.add(doc_id)

                if topic_num not in self.qrels:
                    self.qrels[topic_num] = {}
                if doc_id not in self.qrels[topic_num]:
                    self.qrels[topic_num][doc_id] = []
                self.qrels[topic_num][doc_id].append(int(judgement))

        # Average the ratings
        qrels_avg = {}
        for topic in self.qrels:
            qrels_avg[topic] = {}
            for doc_id, ratings in self.qrels[topic].items():
                if len(ratings) > 1:
                    print(f'{len(ratings)} ratings for doc: {doc_id}')
                qrels_avg[topic][doc_id] = int(sum(ratings) / len(ratings))

        self.qrels = qrels_avg

        for topic in self.qrels:
            for doc_id, avg_rating in self.qrels[topic].items():
                if avg_rating >= 1:
                    self.topic2doc_ids[str(topic)].add(doc_id)

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

    @staticmethod
    def evaluate_own_metrics(found, gold):
        if len(found) == 0:
            return 0, 0, 0

        tp, fp, fn = 0, 0, 0
        for d in found:
            if d in gold:
                tp += 1
            else:
                fp += 1

        for d in gold:
            if d not in found:
                fn += 1

        if tp > 0 or fp > 0:
            precision = tp / (tp + fp)
        else:
            precision = 0
        if tp > 0 or fn > 0:
            recall = tp / (tp + fn)
        else:
            recall = 0
        if precision > 0 or recall > 0:
            f1 = (2 * precision * recall) / (precision + recall)
        else:
            f1 = 0
        return precision, recall, f1

    def evaluate(self, measures, verbose=True) -> [dict, dict]:
        result = dict()
        evaluator = pytrec_eval.RelevanceEvaluator(self.qrels, measures)

        if verbose: print(f'Benchmark has {len(self.relevant_document_ids)} documents')
        bm_results = {}
        bm_results_relaxed = {}
        enum_topics = enumerate(
            sorted([t for t in self.topics if str(t.number) in self.qrels], key=lambda x: int(x.number)))
        if not verbose:
            enum_topics = tqdm(enum_topics, total=len(self.qrels))

        for idx, topic in enum_topics:
            # skip not relevant topics
            # if str(topic.number) not in self.qrels:
            #     if verbose: print(f'Topic {topic.number} not relevant for benchmark')
            #     continue
            # if str(topic.number) == '2':
            #    continue
            query_str = topic.get_test_data()
            # Todo: hack
            # query_str = query_str.replace('coronavirus', 'covid-19')

            if verbose:
                print('--' * 60)
                print(f'Topic {str(topic.number)}: {query_str} \n')
            # print(f'Topic {str(topic.number)}: {query_str} \n')
            queries = translation.translate_keyword_query(query_str, verbose=False)

            # search best query
            best_prec, best_recall, best_f1 = -1, -1, -1
            for q in queries:
                q_document_ids = {str(d) for d in
                                  self.evaluation_graph.compute_query(q)}  # convert doc ids to strings here
                q_document_ids = q_document_ids.intersection(self.relevant_document_ids)
                doc_ids_relevant_for_topic = self.topic2doc_ids[str(topic.number)]
                prec, recall, f1 = Benchmark.evaluate_own_metrics(found=q_document_ids, gold=doc_ids_relevant_for_topic)

                best_strategy_found = []
                if prec > best_prec:
                    best_prec = prec
                    best_strategy_found.append("best_precision")
                if recall > best_recall:
                    best_recall = recall
                    best_strategy_found.append("best_recall")
                if f1 > best_f1:
                    best_f1 = f1
                    best_strategy_found.append("best_f1")

                for s in best_strategy_found:
                    if s not in bm_results:
                        bm_results[s] = {}
                    if topic.number not in bm_results[s]:
                        bm_results[s][topic.number] = {}

                    bm_results[s][topic.number]["doc_ids_retrieved"] = len(q_document_ids)
                    bm_results[s][topic.number]["doc_ids_relevant"] = len(doc_ids_relevant_for_topic)
                    bm_results[s][topic.number]["query"] = str(q)
                    bm_results[s][topic.number]["query_org"] = query_str
                    bm_results[s][topic.number]['metrics'] = {}
                    bm_results[s][topic.number]['metrics']["precision"] = prec
                    bm_results[s][topic.number]['metrics']["recall"] = recall
                    bm_results[s][topic.number]['metrics']["f1"] = f1

            no_queries = len(queries)
            for rank in USED_RANKING_STRATEGIES:
                # Get the most relevant query
                qr = rank.rank_queries(queries)
                if len(qr) > 0:
                    q = qr[0]
                    q_document_ids = {str(d) for d in
                                      self.evaluation_graph.compute_query(q)}  # convert doc ids to strings here
                else:
                    q = Query()
                    q_document_ids = set()  # no hits because no query was returned

                found_in_dg = len(q_document_ids)
                # Restrict document ids to benchmark relevant ids
                q_document_ids = q_document_ids.intersection(self.relevant_document_ids)

                doc_ids_relevant_for_topic = self.topic2doc_ids[str(topic.number)]
                if verbose: print(
                    f'{len(q_document_ids)} / {len(doc_ids_relevant_for_topic)} relevant document ids for query: {q} (found {found_in_dg} matches in DB) ')
                topic_res = {d: 2.0 for d in q_document_ids}

                result[str(topic.number)] = topic_res  # self._normalize_data(topic_res)
                if verbose: print('\nResults:')

                if rank.NAME not in bm_results:
                    bm_results[rank.NAME] = {}

                prec, recall, f1 = Benchmark.evaluate_own_metrics(found=q_document_ids,
                                                                  gold=doc_ids_relevant_for_topic)

                bm_results[rank.NAME][topic.number] = {}
                bm_results[rank.NAME][topic.number]['no_queries'] = no_queries
                bm_results[rank.NAME][topic.number]['metrics'] = evaluator.evaluate({str(topic.number): topic_res})[
                    str(topic.number)]
                bm_results[rank.NAME][topic.number]['metrics']["precision"] = prec
                bm_results[rank.NAME][topic.number]['metrics']["recall"] = recall
                bm_results[rank.NAME][topic.number]['metrics']["f1"] = f1
                bm_results[rank.NAME][topic.number]["doc_ids_retrieved"] = len(q_document_ids)
                bm_results[rank.NAME][topic.number]["doc_ids_relevant"] = len(doc_ids_relevant_for_topic)
                bm_results[rank.NAME][topic.number]["query"] = str(q)
                bm_results[rank.NAME][topic.number]["query_org"] = query_str
                if verbose: print(bm_results[rank.NAME][topic.number]['metrics'])

                for allowed_operations in ALLOWED_DELETE_OPERATIONS:
                    q_rel_document_ids = set()
                    # set to remove duplicated relaxed queries
                    rel_queries = list(set(Query.relax_query(q, delete_operations=allowed_operations)))
                    for r_q in rel_queries:
                        q_rel_document_ids.update({str(d) for d in self.evaluation_graph.compute_query(r_q)})

                    # Restrict document ids to benchmark relevant ids
                    q_rel_document_ids = q_rel_document_ids.intersection(self.relevant_document_ids)
                    if verbose: print(f'\nComputed {len(rel_queries)} relaxed queries resulting in:')
                    q_rel_combined = q_rel_document_ids.union(q_document_ids)
                    if verbose: print(
                        f'{len(q_rel_document_ids)} / {len(doc_ids_relevant_for_topic)} relevant document ids for relaxed queries. ')
                    topic_res_relaxed = {d: 2.0 for d in q_document_ids}
                    # and add all relaxed results with a relevance score of 1
                    topic_res_relaxed.update({d: 1.0 for d in q_rel_document_ids})

                    if rank.NAME not in bm_results_relaxed:
                        bm_results_relaxed[rank.NAME] = {}
                    if allowed_operations not in bm_results_relaxed[rank.NAME]:
                        bm_results_relaxed[rank.NAME][allowed_operations] = {}

                    prec, recall, f1 = Benchmark.evaluate_own_metrics(found=q_rel_combined,
                                                                      gold=doc_ids_relevant_for_topic)

                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number] = {}

                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]['no_queries'] = no_queries
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]['metrics'] = \
                        evaluator.evaluate({str(topic.number): topic_res_relaxed})[str(topic.number)]
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]['metrics']["precision"] = prec
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]['metrics']["recall"] = recall
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]['metrics']["f1"] = f1
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]["query"] = ' OR '.join(
                        [str(q_r) for q_r in rel_queries])
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]["query_org"] = query_str
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]["doc_ids_retrieved"] = len(
                        q_rel_combined)
                    bm_results_relaxed[rank.NAME][allowed_operations][topic.number]["doc_ids_relevant"] = len(
                        doc_ids_relevant_for_topic)
                    if verbose: print(bm_results_relaxed[rank.NAME][allowed_operations][topic.number]['metrics'])

                    # search best relaxed query
                    best_prec, best_recall, best_f1 = -1, -1, -1
                    for q in rel_queries:
                        q_document_ids = {str(d) for d in
                                          self.evaluation_graph.compute_query(q)}  # convert doc ids to strings here
                        q_document_ids = q_document_ids.intersection(self.relevant_document_ids)
                        doc_ids_relevant_for_topic = self.topic2doc_ids[str(topic.number)]
                        prec, recall, f1 = Benchmark.evaluate_own_metrics(found=q_document_ids,
                                                                          gold=doc_ids_relevant_for_topic)

                        best_strategy_found = []
                        if prec > best_prec:
                            best_prec = prec
                            best_strategy_found.append("best_precision")
                        if recall > best_recall:
                            best_recall = recall
                            best_strategy_found.append("best_recall")
                        if f1 > best_f1:
                            best_f1 = f1
                            best_strategy_found.append("best_f1")

                        for s in best_strategy_found:
                            if s not in bm_results_relaxed:
                                bm_results_relaxed[s] = {}
                            if allowed_operations not in bm_results_relaxed[s]:
                                bm_results_relaxed[s][allowed_operations] = {}
                            if topic.number not in bm_results_relaxed[s][allowed_operations]:
                                bm_results_relaxed[s][allowed_operations][topic.number] = {}

                            bm_results_relaxed[s][allowed_operations][topic.number]["doc_ids_retrieved"] = len(
                                q_document_ids)
                            bm_results_relaxed[s][allowed_operations][topic.number]["doc_ids_relevant"] = len(
                                doc_ids_relevant_for_topic)
                            bm_results_relaxed[s][allowed_operations][topic.number]["query"] = str(q)
                            bm_results_relaxed[s][allowed_operations][topic.number]["query_org"] = query_str
                            bm_results_relaxed[s][allowed_operations][topic.number]['metrics'] = {}
                            bm_results_relaxed[s][allowed_operations][topic.number]['metrics']["precision"] = prec
                            bm_results_relaxed[s][allowed_operations][topic.number]['metrics']["recall"] = recall
                            bm_results_relaxed[s][allowed_operations][topic.number]['metrics']["f1"] = f1

        # TODO normalize received data
        # TODO evaluate and return
        return bm_results, bm_results_relaxed

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
        if use_fulltext:
            self.evaluation_graph = covid19_fulltext_graph
            name = name + "_fulltext"
        else:
            self.evaluation_graph = covid19_abstract_graph

        super().__init__(TREC_COVID_DIR, topics_file, qrel_file, name=name)
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

            self.topics.append(PrecisionMedTopic(number, disease, gene, treatment))

    def analyze(self, path):
        entity_tagger = EntityTaggerJCDL.instance()
        results = {}

        def tag_or_none(entity_id):
            try:
                return list(entity_tagger.tag_entity(entity_id))
            except KeyError:
                return None

        topic_count = 0
        type_counter = [0, 0, 0]
        for topic in self.topics:
            if str(topic.number) in self.qrels:
                topic_count += 1
                results[topic.number] = {}
                for idx, entity in enumerate([topic.disease, topic.treatment, topic.gene]):
                    entity_ids = tag_or_none(entity)
                    results[topic.number][entity] = entity_ids
                    if entity_ids:
                        type_counter[idx] += 1

        results["summary"] = {}
        results["summary"]["topic_count"] = topic_count
        results["summary"]["mapped_diseases"] = type_counter[0]
        results["summary"]["mapped_treatments"] = type_counter[1]
        results["summary"]["mapped_genes"] = type_counter[2]

        file = os.path.join(path, f'analyse_{self.name}.json')
        with open(file, 'wt') as f:
            f.write(json.dumps(results))


class TripClickBenchmark(Benchmark):
    def __init__(self, topics_file, qrel_file):
        super().__init__(TRIP_CLICK_DIR, topics_file, qrel_file, name="TripClick")

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
                    if doc_id not in self.qrels[topic_num]:
                        self.qrels[topic_num][doc_id] = []
                    self.qrels[topic_num][doc_id].append(int(judgement))

        qrels_avg = {}
        # Average the ratings
        for topic in self.qrels:
            qrels_avg[topic] = {}
            for doc_id, ratings in self.qrels[topic].items():
                if len(ratings) > 1:
                    print(f'{len(ratings)} ratings for doc: {doc_id}')
                qrels_avg[topic][doc_id] = int(sum(ratings) / len(ratings))

        self.qrels = qrels_avg

        for topic in self.qrels:
            for doc_id, avg_rating in self.qrels[topic].items():
                if avg_rating >= 1:
                    self.topic2doc_ids[str(topic)].add(doc_id)


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
        if 'precision-med' in bm_list:
            self.benchmarks.append(PrecisionMedBenchmark('topics2020.xml', 'qrels-reduced-phase1-treceval-2020.txt'))
        if 'trec-genomics' in bm_list:
            self.benchmarks.append(TRECGenomicsBenchmark('2007topics.txt', 'trecgen2007.all.judgments.tsv.txt'))
        if 'trip-click' in bm_list:
            self.benchmarks.append(TripClickBenchmark(['topics.head.test.txt', 'topics.head.val.txt'],
                                                      ['qrels.raw.head.test.txt', 'qrels.raw.head.val.txt']))

    @staticmethod
    def add_summary_to_metric_dict(bm_result):
        # compute summary per ranking strategy
        for ranking in bm_result:
            summary_dict = {"topics_answered": [], "topics_not_answered": [], "sum_all": {}, "sum_answered": {}}
            answered, not_answered = 0, 0
            for topic, topic_dict in bm_result[ranking].items():
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
            total_topics = len(bm_result[ranking])
            for metric in summary_dict["sum_all"]:
                summary_dict["sum_all"][metric] /= total_topics

            # Normalize result
            for metric in summary_dict['sum_answered']:
                summary_dict['sum_answered'][metric] /= answered

            bm_result[ranking]['summary'] = summary_dict
            bm_result[ranking]['summary']["answered"] = answered
            bm_result[ranking]['summary']["not answered"] = not_answered

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
            bm_result, bm_result_relaxed = bm.evaluate(self.measures, verbose=False)
            BenchmarkRunner.add_summary_to_metric_dict(bm_result)
            for alo in bm_result_relaxed:
                BenchmarkRunner.add_summary_to_metric_dict(bm_result_relaxed[alo])

            if self.path is not None:
                benchmark_name = bm.name
                date = datetime.now()
                filename = f'{benchmark_name}_results_{date.year}.{date.month}.{date.day}.json'
                filename = os.path.join(self.path, filename)

                print(f'Writing results to {filename}')
                with open(filename, 'w') as file:
                    file.write(json.dumps(bm_result))

                filename_relaxed = f'{benchmark_name}_relaxed_results_{date.year}.{date.month}.{date.day}.json'
                filename_relaxed = os.path.join(self.path, filename_relaxed)
                print(f'Writing relaxed results to {filename_relaxed}')
                with open(filename_relaxed, 'w') as file:
                    file.write(json.dumps(bm_result_relaxed))

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
