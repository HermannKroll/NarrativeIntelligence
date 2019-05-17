import logging
import os
import re
import subprocess
from datetime import datetime
from shutil import copyfile
from time import sleep

from config import Config

OUTPUT_INTERVAL = 30

logger = logging.getLogger("preprocessing")


def get_gnorm_progess(output_dir):
    return len([f for f in os.listdir(output_dir) if f.endswith(".txt")])


def get_taggerone_progress(offset, log_file):
    with open(log_file) as f:
        content = f.read()
    matches = re.findall("INFO (\d+)-\d+\n", content)
    progress = len(set(matches))
    return offset + progress


def create_batch_file(batch, batch_file, translation_dir):
    skipped = []
    for fn in batch:
        filename = os.path.join(translation_dir, fn)
        if os.path.exists(filename):
            with open(filename) as f_doc:
                with open(batch_file, "a+") as f_batch:
                    f_batch.write(f_doc.read())
        else:
            skipped.append(filename)
    return skipped


def thread_tag_chemicals_diseases(config, translation_dir, batch_dir, output_dir, log_dir, start_with=None):
    """
    Use TaggerOne to tag chemicals and diseases for PubMedCentral documents contained in ``translation_dir``.

    Method scans the directory and creates a batch iteratively. These batches are saved to ``batch_dir``.
    Only existing documents are collected (for the case they are deleted by GNormPlus).

    Then, TaggerOne is started and the method waits until the process has finished.
    For the case that the process received a SIGKILL signal, the complete method is exited.
    For the case that the process terminated with "1" (indicating an error), the last processed document is skipped and
    the process restarts. The batch now begins with the document *after* the document which produced the error.

    The documents are sorted and started in monotone order.

    :param start_with: ID (PMCxxxxx) of the document to start with (None = start with first)
    :param config: Config object
    :param translation_dir: Path to directory with PubMedCentral files in PubTator format
    :param batch_dir: Directory where the batches are saved (must be writeable)
    :param output_dir: Directory where the tagged results are saved (must be writeable)
    :param log_dir: Log directory (must be writeable)
    :return:
    """
    files = sorted(f for f in os.listdir(translation_dir) if f.endswith(".txt"))
    files_total = len(files)
    first = "{}.txt".format(start_with) if start_with else files[0]
    keep_tagging = True
    skipped_files = []
    start_time = datetime.now()

    while keep_tagging:
        # Generate batch
        ext = first.split(".")[-1]
        batch_name = "batch.{:03d}.{}".format(files.index(first), ext)
        batch_file = os.path.join(batch_dir, batch_name)
        batch = files[files.index(first):files.index(first) + config.tagger_one_batch_size]
        skipped = create_batch_file(batch, batch_file, translation_dir)
        skipped_files.extend(skipped)

        # Start Tagging
        log_file = os.path.join(log_dir, "taggerone.{}.log".format(files.index(first)))
        with open(log_file, "w") as f_log:
            # Start process
            output_file = os.path.join(output_dir, batch_name)
            command = "{} PubTator {} {} {}".format(config.tagger_one_script, config.tagger_one_model, batch_file,
                                                    output_file)
            sp_args = ["/bin/bash", "-c", command]
            process = subprocess.Popen(sp_args, cwd=config.tagger_one_root, stdout=f_log, stderr=f_log)
            logger.debug("Starting TaggerOne {}".format(process.args))

            # Wait until finished
            while process.poll() is None:
                sleep(OUTPUT_INTERVAL)
                progress = get_taggerone_progress(files.index(first), log_file)
                logger.info("TaggerOne progress {}/{}".format(progress, files_total))
            logger.debug("TaggerOne thread for {} exited with code {}".format(batch_file, process.poll()))

        # Process terminated by user
        if process.poll() == -9 or process.poll() == 137:
            logger.info("Received SIGKILL. Stopping TaggerOne ...")
            keep_tagging = False

        # Process quit by exception
        if process.poll() == 1:
            # Remove problematic document
            with open(log_file) as f_log:
                content = f_log.read()
            matches = re.findall(r"INFO (\d+)-\d+", content)
            if matches:
                last_fn = "PMC{}.txt".format(matches[-1])
                last_file = os.path.join(translation_dir, last_fn)
                skipped_files.append(last_file)
                logger.debug("TaggerOne exception in file {}".format(last_file))
                copyfile(log_file, "{}.{}".format(log_file, len(skipped_files)))
                if os.path.exists(last_file):
                    os.remove(last_file)
                # Remove failed tagging from output
                with open(output_file) as f:
                    lines = f.readlines()
                with open(output_file, "w") as f:
                    if re.findall(r"\d+\|a\|", lines[-1]):
                        f.writelines(lines[:-2])
                    elif re.findall(r"\d+\|t\|", lines[-1]):
                        f.writelines(lines[:-1])
                    else:
                        f.writelines(lines)
                        logger.warning("Removing bad document from {} failed ({})".format(output_file, last_fn))

                if files.index(last_fn) == len(files) - 1:
                    keep_tagging = False
                else:
                    keep_tagging = process.poll()
                    first = files[files.index(last_fn) + 1]
            else:
                # No file processed, assume another error
                # keep_tagging = False
                first = files[files.index(first) + 1]
                logger.error("No files processed. Continue with {}".format(first))

        if process.poll() == 0:
            if files[-1] == batch[-1]:
                keep_tagging = False
            else:
                first = files[files.index(batch[-1]) + 1]

    end_time = datetime.now()
    logger.info("TaggerOne finished in {} ({} files total, {} errors)".format(end_time - start_time,
                                                                              len(files) - len(skipped_files),
                                                                              len(skipped_files)))


def thread_tag_genes(config: Config, input_dir, output_dir, log_dir):
    """
    Method starts a GNormPlus instance with all files from ``input_dir`` and writes the result back to ``output_dir``.
    Log files are written into the directory ``log_dir``.

    If an error occurs during the execution of GNormPlus, the exit code is evaluated. If it's 1 the last processed
    file is removed and the instance is going to be restarted. If no file was processed the thread is cancelled and
    a manual analysis is recommended (maybe an OutOfMemoryException?).

    :param config: Config object
    :param input_dir: Input directory with PubMedCentral files
    :param output_dir: Output directory (must be writeable)
    :param log_dir: Log directory (must be writeable)
    """
    gnorm_log = os.path.join(log_dir, "gnorm.log")
    skipped_files = []
    latest_exit_code = 1
    files_total = len(os.listdir(input_dir))
    start_time = datetime.now()

    while latest_exit_code == 1:
        with open(gnorm_log, "w") as f_log:
            # Start GNormPlus
            sp_args = ["java", "-Xmx100G", "-Xms30G", "-jar", config.gnorm_jar, input_dir, output_dir,
                       config.gnorm_setup]
            process = subprocess.Popen(sp_args, cwd=config.gnorm_root, stdout=f_log, stderr=f_log)
            logger.debug("Starting GNormPlus {}".format(process.args))

            # Wait until finished
            while process.poll() is None:
                sleep(OUTPUT_INTERVAL)
                progress = get_gnorm_progess(output_dir)
                logger.info("GNormPlus progress {}/{}".format(progress, files_total))
            logger.debug("GNormPlus exited with code {}".format(process.poll()))
            latest_exit_code = process.poll()

        if process.poll() == 1:
            # Remove problematic document
            with open(gnorm_log) as f_log:
                content = f_log.read()
            matches = re.findall(r"/.*?PMC\d+\.txt", content)
            if matches:
                last_file = matches[-1]
                skipped_files.append(last_file)
                logger.debug("GNormPlus exception in file {}".format(last_file))
                copyfile(gnorm_log, "{}.{}".format(gnorm_log, len(skipped_files)))
                os.remove(last_file)
                latest_exit_code = process.poll()
            else:
                # No file processed, assume another error
                latest_exit_code = None
                logger.error("No files processed. Assuming an unexpected exception")

    end_time = datetime.now()
    logger.info("GNormPlus finished in {} ({} files total, {} errors)".format(end_time - start_time,
                                                                              files_total,
                                                                              len(skipped_files)))
