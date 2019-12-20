import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from shutil import copyfile
from time import sleep

from narraint.backend import types
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.pubtator.count import get_document_ids


class NoRemainingDocumentError(Exception):
    """
    Error class indicating that no unfinished documents exist.
    """
    pass


# TODO: Ensure that documents are not processed twice. List with processed IDs/files?
class TaggerOne(BaseTagger):
    """
    TaggerOne can tag chemicals and diseases.
    """
    TYPES = (types.CHEMICAL, types.DISEASE)
    __name__ = "TaggerOne"
    __version__ = "0.2.1"

    def get_tags(self):
        return self._get_tags(self.out_dir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "taggerone_in")
        self.out_dir = os.path.join(self.root_dir, "taggerone_out")
        self.batch_dir = os.path.join(self.root_dir, "taggerone_batches")
        self.log_file = os.path.join(self.log_dir, "taggerone.log")
        self.skipped_files = []

    def prepare(self, resume=False):
        """
        Copy files into the input directory, because we delete them if they cause TaggerOne to fail.
        :param resume: Flag wheter to resume the tagging
        """
        if not resume:
            os.mkdir(self.in_dir)
            new_files = set()
            for fn in self.files:
                target = os.path.join(self.in_dir, fn.split("/")[-1])
                new_files.add(target)
                shutil.copy(fn, target)
            self.files = new_files
            os.mkdir(self.out_dir)
            os.mkdir(self.batch_dir)
        else:
            raise NotImplementedError("Resuming TaggerOne is not implemented.")

    def get_finished_ids(self):
        """
        Function returns the set of precessed ids. This is the union of the IDs in the output directory and the IDs
        in the log file (which are currently not written but processed)
        :return: Set of IDs
        """
        ids_dir = get_document_ids(self.out_dir)
        ids_log = set()
        if os.path.exists(self.log_file):
            with open(self.log_file) as f:
                content = f.read()
            ids_log = set(int(x) for x in re.findall(r"INFO (\d+)-\d+\n", content))
        return ids_dir.union(ids_log)

    def get_progress(self):
        """
        Returns the number of already processed IDs.
        """
        return len(self.get_finished_ids())

    def create_batch(self):
        """
        Function creates a random batch in the size of the configured batch size.
        First, the set of not processed IDs is created, converted to a list and the first k IDs are chosen.
        Then, the list of filenames is created and if its non-empty, the batch file is written.

        Method returns the batch ID and the location of the batch file.
        :return: Tuple of batch ID and batch
        """
        finished_ids = self.get_finished_ids()
        unfinished_ids = list(self.id_set.difference(finished_ids))
        batch_ids = unfinished_ids[:self.config.tagger_one_batch_size]
        batch = [self.mapping_id_file[doc_id] for doc_id in batch_ids]
        self.logger.debug(f"Variable finished_ids contains {len(finished_ids)} elements")
        self.logger.debug(f"Variable unfinished_ids contains {len(unfinished_ids)} elements")
        batch_id = None
        batch_file = None
        if batch:
            num_skipped = 0
            batch_id = uuid.uuid1()
            batch_file = self.get_batch_file(batch_id)
            # Write batch
            for fn in batch:
                filename = os.path.join(self.in_dir, fn)
                if os.path.exists(filename):  # Important if file was deleted
                    with open(filename) as f_doc:
                        with open(batch_file, "a+") as f_batch:
                            f_batch.write(f_doc.read())
                else:
                    self.skipped_files.append(filename)
                    num_skipped += 1
            self.logger.debug("Created batch ({}, {} files, {} skipped)".format(batch_id, len(batch), num_skipped))
        return batch_id, batch_file

    def get_output_file(self, batch_id):
        return os.path.join(self.out_dir, "batch.{}.txt".format(batch_id))

    def get_batch_file(self, batch_id):
        return os.path.join(self.batch_dir, "batch.{}.txt".format(batch_id))

    def run_tagging(self, batch_id, batch_file):
        """
        Method runs the actual tagging process and returns the TaggerOne exit code.

        :param batch_id: Document ID of first document in batch
        :param batch_file: Path to batch file
        :return: Exit status of TaggerOne
        """
        with open(self.log_file, "w") as f_log:
            command = "{} Pubtator {} {input} {out}".format(
                self.config.tagger_one_script,
                self.config.tagger_one_model,
                input=batch_file,
                out=self.get_output_file(batch_id),
            )
            sp_args = ["/bin/bash", "-c", command]
            process = subprocess.Popen(sp_args, cwd=self.config.tagger_one_root, stdout=f_log, stderr=f_log)
            self.logger.debug("Starting TaggerOne {}".format(process.args))

            # Wait until finished
            while process.poll() is None:
                sleep(self.OUTPUT_INTERVAL)
                progress = self.get_progress()
                self.logger.info("TaggerOne progress {}/{}".format(progress, len(self.files)))
            self.logger.debug("TaggerOne thread for {} exited with code {}".format(batch_file, process.poll()))
        return process.poll()

    def handle_error(self):
        """
        Method performs the error handling if TaggerOne quits with exit code 1.
        :return: Flag whether to continue tagging
        """
        keep_tagging = True
        with open(self.log_file) as f_log:
            content = f_log.read()
        matches = re.findall(r"INFO (\d+)-\d+", content)
        self.logger.debug("Searching log file {} ({} matches found)".format(self.log_file, len(matches)))
        if matches:
            last_file = self.mapping_id_file[matches[-1]]
            self.skipped_files.append(last_file)
            self.logger.debug("TaggerOne exception in file {}".format(last_file))
            copyfile(self.log_file, "{}.{}".format(self.log_file, len(self.skipped_files)))
            if os.path.exists(last_file):
                os.remove(last_file)
                self.logger.debug("Successfully deleted {}".format(last_file))
            else:
                self.logger.debug("Failed to delete {}. File is already deleted.".format(last_file))
        else:
            # No file processed, assume another error
            self.logger.error("No files processed")
            # Generate batch
            batch_id, batch_file = self.create_batch()
            if not batch_id:
                keep_tagging = False
                self.logger.info("Stopping due to no new batch created")
        return keep_tagging

    def run(self):
        """
        Use TaggerOne to tag chemicals and diseases.

        Method creates a batch iteratively. These batches are saved to ``batch_dir``.
        Only existing documents are collected (for the case they are deleted by GNormPlus).

        Then, TaggerOne is started and the method waits until the process has finished.
        For the case that the process received a SIGKILL signal, the complete method is exited.
        For the case that the process terminated with "1" (indicating an error), the last processed document is deleted
        and the process restarts. We create a new batch.
        """
        keep_tagging = True
        start_time = datetime.now()

        # Generate first batch
        batch_id, batch_file = self.create_batch()
        while keep_tagging and batch_id:
            # Start Tagging
            self.log_file = os.path.join(self.log_dir, "taggerone.{}.log".format(batch_id))
            exit_code = self.run_tagging(batch_id, batch_file)

            # Check process exit code
            if exit_code == 0:
                # Process finished successfully
                if self.get_progress() + len(self.skipped_files) == len(self.files):
                    keep_tagging = False
            elif exit_code == 1:
                # Process quit by exception
                keep_tagging = self.handle_error()
            elif exit_code == -9 or exit_code == 137:
                # Process terminated by user
                self.logger.info("Received SIGKILL. Stopping TaggerOne ...")
                keep_tagging = False

            # Create new batch
            batch_id, batch_file = self.create_batch()

        end_time = datetime.now()
        self.logger.info("TaggerOne finished in {} ({} files total, {} errors)".format(
            end_time - start_time,
            len(self.files) - len(self.skipped_files),
            len(self.skipped_files)))
