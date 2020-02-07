import sys
from datetime import datetime, timedelta


def print_progress_with_eta(text, current, size, start_time, print_every_k=1000):
    percentage = (current + 1.0) / size * 100.0
    if current % print_every_k == 0:
        elapsed_seconds = (datetime.now() - start_time).seconds + 1
        seconds_per_doc = elapsed_seconds / (current + 1.0)
        remaining_seconds = (size - current) * seconds_per_doc
        eta = (start_time + timedelta(seconds=remaining_seconds)).strftime("%Y-%m-%d %H:%M")

        sys.stdout.write("\r{} ... {:0.1f} % (ETA {})".format(text, percentage, eta))
        sys.stdout.flush()