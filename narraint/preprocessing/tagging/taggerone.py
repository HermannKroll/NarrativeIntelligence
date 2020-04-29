import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from shutil import copyfile
from time import sleep

from narraint.entity import enttypes
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.progress import print_progress_with_eta
from narraint.pubtator.count import get_document_ids
from narraint.pubtator.regex import DOCUMENT_ID


class NoRemainingDocumentError(Exception):
    """
    Error class indicating that no unfinished documents exist.
    """
    pass


class TaggerOne(BaseTagger):
    """
    TaggerOne can tag chemicals and diseases.
    """
    TYPES = (enttypes.CHEMICAL, enttypes.DISEASE)
    __name__ = "TaggerOne"
    __version__ = "0.2.1"
    TAGGER_ONE_RETRIES = 2

    def get_tags(self):
        return self._get_tags(self.out_dir)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_dir = os.path.join(self.root_dir, "taggerone_in")
        self.out_dir = os.path.join(self.root_dir, "taggerone_out")
        self.batch_dir = os.path.join(self.root_dir, "taggerone_batches")
        self.log_file = os.path.join(self.log_dir, "taggerone.log")
        self.skipped_files = set()
        self.skipped_file_ids = set()
        self.current_retry = 0
        self.start_time = datetime.now()

    def prepare(self, resume=False):
        """
        Copy files into the input directory, because we delete them if they cause TaggerOne to fail.
        :param resume: Flag whether to resume the tagging
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
        unfinished_ids = self.id_set.difference(finished_ids)
        # ignore skipped file ids
        unfinished_ids = list(unfinished_ids.difference(self.skipped_file_ids))
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
                with open(filename) as f_doc:
                    with open(batch_file, "a+") as f_batch:
                        f_batch.write(f_doc.read())

            self.logger.debug("Created batch ({}, {} files)".format(batch_id, len(batch)))
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
                print_progress_with_eta("TaggerOne tagging", self.get_progress(), len(self.files), self.start_time,
                                        print_every_k=1, logger=self.logger)
            self.logger.debug("TaggerOne thread for {} exited with code {}".format(batch_file, process.poll()))
        return process.poll()

    def _ignore_document(self, document_id):
        """
        Deletes a document from the TaggerOne input
        The document will not be tagged - but the process continues Tagging the other documents
        :param document_id:
        :return:
        """
        self.logger.debug("Last match: {}".format(document_id))
        self.skipped_file_ids.add(document_id)
        last_file = self.mapping_id_file[int(document_id)]
        self.logger.warning("TaggerOne exception in file {}".format(last_file))
        self.skipped_files.add(last_file)
        copyfile(self.log_file, "{}.{}".format(self.log_file, len(self.skipped_files)))
        if os.path.exists(last_file):
            os.remove(last_file)
            self.logger.debug("Successfully deleted {}".format(last_file))
        else:
            self.logger.debug("Failed to delete {}. File is already deleted.".format(last_file))

    def handle_error(self, last_batch_file):
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
            self.logger.warning("TaggerOne crashed - skipping last file: {}".format(matches[-1]))
            # we skip the last document
            self._ignore_document(matches[-1])
        else:
            # No file processed, assume another error
            # Try TaggerOne again
            self.logger.warning("No files processed")
            # To prevent a endless repetition -> count the retries
            # If we have to many retries - skip the first document of the current batch
            if self.current_retry >= TaggerOne.TAGGER_ONE_RETRIES:
                self.logger.warning('File crashed 3 times - Skip first file of current batch')
                # Search the first document id in the last batch
                with open(last_batch_file, 'rt') as f_l_batch:
                    last_batch_file_content = f_l_batch.read()
                matches = re.findall(DOCUMENT_ID, last_batch_file_content)
                if matches:
                    for match in matches:
                        self._ignore_document(match)
                        self.current_retry = 0
                else:
                    self.logger.error('Critical error - there is no document id in the last batch - stopping')
                    keep_tagging = False
            else:
                # increase counter - it is a retry
                self.current_retry += 1
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
        For the case that the process received a SIGKILL signal (out of memory), TaggerOne will be restarted.
        For the case that the process terminated with "1" (indicating an error), the last processed document is deleted
        and the process restarts. We create a new batch.
        """
        keep_tagging = True
        self.start_time = datetime.now()

        # Generate first batch
        batch_id, batch_file = self.create_batch()
        while keep_tagging and batch_id:
            # Start Tagging
            self.log_file = os.path.join(self.log_dir, "taggerone.{}.log".format(batch_id))
            exit_code = self.run_tagging(batch_id, batch_file)

            # Check process exit code
            if exit_code == 0:
                self.current_retry = 0
                # Process finished successfully
                if self.get_progress() + len(self.skipped_files) == len(self.files):
                    keep_tagging = False
            elif exit_code == 1:
                # Process quit by exception
                keep_tagging = self.handle_error(batch_file)
            elif exit_code == 137:
                # out of memory exit code
                # let's wait 5 minutes till the process tries to restart
                self.logger.warning('Received out of memory exit code for process - restart in 5 minutes')
                sleep(5*60)
                keep_tagging = self.handle_error(batch_file)
            elif exit_code == -9:
                # Process terminated by user
                self.logger.info("Received SIGKILL. Stopping TaggerOne ...")
                keep_tagging = False

            if keep_tagging:
                # Create new batch
                batch_id, batch_file = self.create_batch()

        end_time = datetime.now()
        self.logger.info("TaggerOne finished in {} ({} files total, {} errors)".format(
            end_time - self.start_time,
            len(self.files) - len(self.skipped_files),
            len(self.skipped_files)))
