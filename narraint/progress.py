import sys
from datetime import datetime, timedelta


def print_progress_with_eta(text, current_idx, size, start_time, print_every_k=1000, logger=None):
    """
    Print progress in percent with an estimated time until the process is done.
    Usually, this function is used when the set of objects to work on is finite.

    :param text: Caption of the task
    :param current_idx: Index of last processed objects. Negative if no object has been processed so far.
    :param size: Total number of objects
    :param start_time: Time of start
    :param print_every_k: Number of objects after which the output should be updated
    :param logger: A logging instance to output progress to
    :return:
    """
    if current_idx % print_every_k == 0:
        if current_idx < 0:
            percentage = 0
            eta = "--"
        else:
            percentage = (current_idx + 1.0) / size * 100.0
            elapsed_seconds = (datetime.now() - start_time).seconds + 1
            seconds_per_doc = elapsed_seconds / (current_idx + 1.0)
            remaining_seconds = (size - current_idx) * seconds_per_doc
            eta = (datetime.now() + timedelta(seconds=remaining_seconds)).strftime("%Y-%m-%d %H:%M")
        if not logger:
            sys.stdout.write("\r{} ... {:0.1f} % (ETA {})".format(text, percentage, eta))
            sys.stdout.flush()
        else:
            logger.info("{} ... {:0.1f} % (ETA {})".format(text, percentage, eta))
