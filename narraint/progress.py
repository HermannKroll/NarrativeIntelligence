import sys
from datetime import datetime, timedelta


def print_progress_with_eta(text, current_idx, size, start_time, print_every_k=1000):
    """
    Print progress in percent with an estimated time until the process is done.
    Usually, this function is used when the set of objects to work on is finite.

    :param text: Caption of the task
    :param current_idx: Index of current objects
    :param size: Total number of objects
    :param start_time: Time of start
    :param print_every_k: Number of objects after which the output should be updated
    :return:
    """
    if current_idx % print_every_k == 0:
        percentage = (current_idx + 1.0) / size * 100.0
        elapsed_seconds = (datetime.now() - start_time).seconds + 1
        seconds_per_doc = elapsed_seconds / (current_idx + 1.0)
        remaining_seconds = (size - current_idx) * seconds_per_doc
        eta = (start_time + timedelta(seconds=remaining_seconds)).strftime("%Y-%m-%d %H:%M")

        sys.stdout.write("\r{} ... {:0.1f} % (ETA {})".format(text, percentage, eta))
        sys.stdout.flush()