import logging
import os
from datetime import date
from narraint.config import LOG_DIR


def configure_logging():
    # Set the root logger to the lowest level (DEBUG) to capture all log messages
    logging.basicConfig(level=logging.DEBUG)
    today = date.today().strftime("%Y-%m-%d")

    err_warn_dir = os.path.join(LOG_DIR, "logging", "errors+warn")
    info_dir = os.path.join(LOG_DIR, "logging", "infos")
    os.makedirs(err_warn_dir, exist_ok=True)
    os.makedirs(info_dir, exist_ok=True)
    error_warn_log_file = os.path.join(err_warn_dir, f"{today}-errors+warn.log")
    info_log_file = os.path.join(info_dir, f"{today}-info.log")

    # Configure the file handlers for different log levels
    error_warn_handler = logging.FileHandler(error_warn_log_file)
    info_handler = logging.FileHandler(info_log_file)
    console_handler = logging.StreamHandler()

    error_warn_handler.setLevel(logging.WARNING)  # Writes warnings and errors
    info_handler.setLevel(logging.DEBUG)  # Writes info and above
    console_handler.setLevel(logging.DEBUG)

    log_format = "%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
    formatter = logging.Formatter(log_format)

    error_warn_handler.setFormatter(formatter)
    info_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    info_handler.addFilter(lambda record: record.levelno <= logging.INFO)

    #Clear any existing handlers from the root logger
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    # Add the file handlers to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(error_warn_handler)
    root_logger.addHandler(info_handler)
    root_logger.addHandler(console_handler)

