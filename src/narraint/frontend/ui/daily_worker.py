import os
import json
import time
import logging
import sys
from datetime import datetime, timedelta

from narraint.config import LOG_DIR
from narraint.queryengine.log_statistics import create_dictionary_of_logs

log_path = os.path.join(LOG_DIR, "daily_logs_cache")
if not os.path.exists(log_path):
    os.makedirs(log_path)

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cache_daily_logs():
    logging.info("Starting the daily log caching process...")
    while True:
        today = datetime.now().date()

        cache_filename = f"daily_logs_cache_{today.strftime('%Y%m%d')}.json"
        cache_file_path = os.path.join(log_path, cache_filename)


        if not os.path.exists(cache_file_path):
            logging.info("Processing log data for today...")
            data = create_dictionary_of_logs()

            with open(cache_file_path, 'w') as cache_file:
                json.dump(data, cache_file, indent=4, default=str)
            logging.info(f"Log data cached successfully at {cache_file_path}")
        else:
            logging.info(f"Cache file for today already exists: {cache_file_path}")

        next_run = datetime.combine(today + timedelta(days=1), datetime.min.time())
        sleep_seconds = (next_run - datetime.now()).total_seconds()
        logging.info(f"Sleeping until next day: {next_run}")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    cache_daily_logs()
