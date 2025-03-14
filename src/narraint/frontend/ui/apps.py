import logging
import os
import subprocess
import sys
import threading

from django.apps import AppConfig

from narraint.logging_config import configure_logging


def log_output(pipe, level):
    for line in iter(pipe.readline, ''):
        logging.log(level, line.strip())


class UiConfig(AppConfig):
    name = 'ui'

    def ready(self):
        configure_logging()

        if len(sys.argv) > 1 and sys.argv[1] in ['collectstatic', 'migrate']:
            logging.info('Skipping dailyWorker initialization')
            return

        logging.info("Spawning the dailyWorker process...")
        daily_worker_path = os.path.join(os.path.dirname(__file__), "daily_worker.py")

        if not self._is_process_running(daily_worker_path):
            python_executable = sys.executable
            process = subprocess.Popen(
                [python_executable, daily_worker_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logging.info("dailyWorker process started.")

            threading.Thread(target=log_output, args=(process.stdout, logging.INFO)).start()
            threading.Thread(target=log_output, args=(process.stderr, logging.ERROR)).start()
        else:
            logging.info("dailyWorker process is already running.")

    @staticmethod
    def _is_process_running(script_path):
        for proc in subprocess.check_output(["ps", "aux"]).splitlines():
            if script_path in str(proc):
                return True
        return False
