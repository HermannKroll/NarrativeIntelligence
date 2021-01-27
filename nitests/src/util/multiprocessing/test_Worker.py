import os
import unittest

import multiprocessing

from narraint import tools
from narraint.util.multiprocessing.ConsumerWorker import ConsumerWorker
from narraint.util.multiprocessing.FileConsumerWorker import FileConsumerWorker
from narraint.util.multiprocessing.ProducerWorker import ProducerWorker
from narraint.util.multiprocessing.Worker import Worker
from nitests import util


class TestWorker(unittest.TestCase):
    def test_single_worker(self):
        def generate_task_src():
            yield from range(1, 1000)

        task_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        prod = ProducerWorker(task_queue, generate_task_src, 10)

        def do_task(task:int):
            return -task

        worker = Worker(task_queue, result_queue, do_task)

        prod.start()
        worker.start()
        for n in range(1,1000):
            self.assertEqual(-n, result_queue.get(block=True, timeout=5))

    def test_dual_worker(self):
        def generate_task_src():
            yield from range(1, 1000)

        task_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        prod = ProducerWorker(task_queue, generate_task_src, 2, 10)

        def do_task(task:int):
            return -task

        worker1 = Worker(task_queue, result_queue, do_task)
        worker2 = Worker(task_queue, result_queue, do_task)


        prod.start()
        worker1.start()
        worker2.start()
        result_set = {-n for n in range(1,1000)}
        for n in range(1,1000):
            res = result_queue.get(block=True, timeout=5)
            self.assertIn(res,result_set)


    def test_10_worker(self):
        def generate_task_src():
            yield from range(1, 1000)

        task_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        prod = ProducerWorker(task_queue, generate_task_src, 10, 10)

        def do_task(task:int):
            return -task

        workers = [Worker(task_queue, result_queue, do_task) for n in range(10)]


        prod.start()
        for worker in workers:
            worker.start()

        result_set = {-n for n in range(1,1000)}
        for n in range(1,1000):
            res = result_queue.get(block=True, timeout=5)
            self.assertIn(res,result_set)

    def test_10_worker_file(self):
        def generate_task_src():
            yield from range(1, 1000)

        task_queue = multiprocessing.Queue()
        result_queue = multiprocessing.Queue()
        prod = ProducerWorker(task_queue, generate_task_src, 10, 10)

        def do_task(task:int):
            return f"-{task}\n"

        workers = [Worker(task_queue, result_queue, do_task) for n in range(10)]

        out_path = tools.proj_rel_path("nitests/tmp/out/multiout.txt")
        os.makedirs(os.path.dirname(out_path))
        consumer = FileConsumerWorker(result_queue, out_path, 10)

        prod.start()
        for worker in workers:
            worker.start()

        consumer.start()
        consumer.join()
        result_set = {-n for n in range(1,1000)}
        with open(out_path) as f:
            for res in f:
                self.assertIn(int(res[:-1]), result_set)
