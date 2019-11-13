import os
import re
import shutil
import subprocess
from datetime import datetime
from shutil import copyfile
from time import sleep

from tagging.base import BaseTagger, finalize_dir


class NoRemainingDocumentError(Exception):
    """
    Error class indicating that no unfinished documents exist.
    """
    pass


class TaggerOne(BaseTagger):
    def finalize(self):
        finalize_dir(self.out_dir, self.result_file, batch_mode=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "taggerone_in")
        self.out_dir = os.path.join(self.root_dir, "taggerone_out")
        self.batch_dir = os.path.join(self.root_dir, "taggerone_batches")
        self.result_file = os.path.join(self.root_dir, "chemicals_diseases.txt")
        self.log_file = os.path.join(self.log_dir, "taggerone.log")
        self.pivot = None

    def prepare(self, resume=False):
        if not resume:
            shutil.copytree(self.translation_dir, self.in_dir)
            os.mkdir(self.out_dir)
            os.mkdir(self.batch_dir)
        else:
            raise NotImplementedError("Resuming TaggerOne is not implemented.")

    def get_progress(self, offset=0):
        with open(self.log_file) as f:
            content = f.read()
        matches = re.findall(r"INFO (\d+)-\d+\n", content)
        progress = len(set(matches))
        return offset + progress

    def create_batch_file(self, batch, batch_file):
        skipped = []
        for fn in batch:
            filename = os.path.join(self.in_dir, fn)
            if os.path.exists(filename):  # Important if file was delted
                with open(filename) as f_doc:
                    with open(batch_file, "a+") as f_batch:
                        f_batch.write(f_doc.read())
            else:
                skipped.append(filename)
        return skipped

    def get_next_pivot(self, last_processed):
        next_pivot = None  # indicating search is not completed
        is_search_completed = False

        while not is_search_completed:
            file_list = sorted(f for f in os.listdir(self.in_dir) if f.endswith(".txt"))
            try:
                next_pivot = next(x for x in file_list if x > last_processed)
            except StopIteration:
                next_pivot = None
                is_search_completed = True
            # Check if pivot exists
            if next_pivot and os.path.exists(os.path.join(self.in_dir, next_pivot)):
                is_search_completed = True

        return next_pivot

    def get_next_document_id(self):
        """
        Method searches the already tagged documents and returns the next document to start with.
        If no ID is found, a ValueError is raised.
        If all documents are already processed, a NoRemainingDocumentError is raised.

        :param translation_dir: Directory with the PubMedCentral PubTator documents
        :param tagger_one_out_dir: Directory with the tagged batches of TaggerOne
        :return: Next ID to work on
        :raises ValueError: if no IDs were found
        :raises NoRemainingDocumentError: if all documents are already processed
        """
        translations = sorted(fn[:-4] for fn in os.listdir(self.translation_dir))

        processed_files = sorted(os.listdir(self.out_dir))
        if processed_files:
            last_batch_file = processed_files[-1]
            last_batch_path = os.path.join(self.out_dir, last_batch_file)
            with open(last_batch_path) as f:
                content = f.read()
            finished_ids = re.findall(r"(\d+)\|t\|", content)
            if finished_ids:
                last_id = "PMC{}".format(finished_ids[-1])
            else:
                raise ValueError("TaggerOne result {} is empty. Please remove manually.".format(last_batch_path))
            last_idx = translations.index(last_id)
            if last_idx == len(translations) - 1:
                raise NoRemainingDocumentError
            return translations[last_idx + 1]
        else:
            return translations[0]

    def run(self, start_with=None):
        """
        Use TaggerOne to tag chemicals and diseases for PubMedCentral documents contained in ``translation_dir``.

        Method scans the directory and creates a batch iteratively. These batches are saved to ``batch_dir``.
        Only existing documents are collected (for the case they are deleted by GNormPlus).

        Then, TaggerOne is started and the method waits until the process has finished.
        For the case that the process received a SIGKILL signal, the complete method is exited.
        For the case that the process terminated with "1" (indicating an error), the last processed document is skipped and
        the process restarts. The batch now begins with the document *after* the document which produced the error.

        The documents are sorted and started in monotone order.

        ---

        If `start_with` is not found, the next available and untagged document is selected.

        :param start_with: ID (PMCxxxxx) of the document to start with (None = start with first)
        """
        files = sorted(f for f in os.listdir(self.in_dir) if f.endswith(".txt"))
        files_total = len(files)
        pivot = "{}.txt".format(start_with) if start_with else files[0]
        keep_tagging = True
        skipped_files = []
        start_time = datetime.now()

        while keep_tagging:
            if not os.path.exists(os.path.join(self.in_dir, pivot)):
                pivot = self.get_next_pivot(pivot)

            # Generate batch
            ext = pivot.split(".")[-1]
            batch_name = "batch.{:03d}.{}".format(files.index(pivot), ext)
            batch_file = os.path.join(self.batch_dir, batch_name)
            batch = files[files.index(pivot):files.index(pivot) + self.config.tagger_one_batch_size]
            skipped = self.create_batch_file(batch, batch_file)
            skipped_files.extend(skipped)
            self.logger.debug("Created batch ({} to {}, {} files, {} skipped)".format(
                batch[0], batch[-1], len(batch), len(skipped)
            ))

            # Start Tagging
            self.log_file = os.path.join(self.log_dir, "taggerone.{}.log".format(files.index(pivot)))
            with open(self.log_file, "w") as f_log:
                # Start process
                output_file = os.path.join(self.out_dir, batch_name)
                command = "{} PubTator {} {} {}".format(self.config.tagger_one_script,
                                                        self.config.tagger_one_model, batch_file,
                                                        output_file)
                sp_args = ["/bin/bash", "-c", command]
                process = subprocess.Popen(sp_args, cwd=self.config.tagger_one_root, stdout=f_log, stderr=f_log)
                self.logger.debug("Starting TaggerOne {}".format(process.args))

                # Wait until finished
                while process.poll() is None:
                    sleep(self.OUTPUT_INTERVAL)
                    progress = self.get_progress(files.index(pivot))
                    self.logger.info("TaggerOne progress {}/{}".format(progress, files_total))
                    self.logger.debug("TaggerOne thread for {} exited with code {}".format(batch_file, process.poll()))

            # Check process exit code
            if process.poll() == 0:
                # Process finished successfully
                if files[-1] == batch[-1]:
                    keep_tagging = False
                else:
                    pivot = self.get_next_pivot(batch[-1])
            elif process.poll() == 1:
                # Process quit by exception
                # Detemine problematic document
                with open(self.log_file) as f_log:
                    content = f_log.read()
                matches = re.findall(r"INFO (\d+)-\d+", content)
                self.logger.debug("Searching log file {} ({} matches found)".format(self.log_file, len(matches)))
                if matches:
                    last_fn = "PMC{}.txt".format(matches[-1])
                    last_file = os.path.join(self.in_dir, last_fn)
                    skipped_files.append(last_file)
                    self.logger.debug("TaggerOne exception in file {}".format(last_file))
                    copyfile(self.log_file, "{}.{}".format(self.log_file, len(skipped_files)))
                    if os.path.exists(last_file):
                        os.remove(last_file)
                        self.logger.debug("Successfully deleted {}".format(last_file))
                    else:
                        self.logger.debug("Failed to delete {}. File is already deleted.".format(last_file))
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
                            self.logger.warning(
                                "Removing bad document {} from batch {} failed".format(last_fn, output_file))

                    pivot = self.get_next_pivot(last_fn)
                else:
                    # No file processed, assume another error
                    # keep_tagging = False
                    self.logger.error("No files processed.")
                    pivot = self.get_next_pivot(pivot)

                if pivot:
                    self.logger.debug("Next document: {}".format(pivot))
                else:
                    self.logger.info("No next document found. Stopping ...")
                    keep_tagging = False
            elif process.poll() == -9 or process.poll() == 137:
                # Process terminated by user
                self.logger.info("Received SIGKILL. Stopping TaggerOne ...")
                keep_tagging = False

        end_time = datetime.now()
        self.logger.info("TaggerOne finished in {} ({} files total, {} errors)".format(end_time - start_time,
                                                                                       len(files) - len(skipped_files),
                                                                                       len(skipped_files)))
