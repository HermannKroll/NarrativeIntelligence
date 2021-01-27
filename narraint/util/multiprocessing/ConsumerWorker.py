import multiprocessing
import queue
from collections import Iterable
from time import sleep

from narraint.util.multiprocessing.Worker import SHUTDOWN_SIGNAL
from narraint.util.multiprocessing.WorkerProcess import WorkerProcess


class ConsumerWorker(WorkerProcess):
    def __init__(self, result_queue: multiprocessing.Queue, consume, no_workers):
        """

        :param result_queue:
        :param consume: Callable, gets result and consumes it
        :param prepare:
        :param shutdown:
        """
        super().__init__()

        self.result_queue = result_queue
        self.__consume = consume
        self.__running = True
        self.__no_workers=no_workers

    def run(self):
        shutdown_signal_count = 0
        while self.__running:
            try:
                res = self.result_queue.get(timeout=1)
                if res == SHUTDOWN_SIGNAL:
                    shutdown_signal_count += 1
                    if shutdown_signal_count == self.__no_workers:
                        self.__running = False
                else:
                    self.__consume(res)
            except queue.Empty:
                sleep(0.1)
                continue

    def stop(self):
        self.__running = False