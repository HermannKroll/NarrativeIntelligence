import os
from shutil import copy
from narraint.pubtator.count import count_documents
from narraint.pubtator.split import split

def create_parallel_dirs(root, number, prefix, *subdirs):
    """
    Creates number identical subdirectories named <prefix><index> containing subdirectories specified with the names
    given in *subdirs.
    :param root: The directory where the subdirectories are to be created
    :param number: The number of identical subdirs to be created
    :param prefix: The prefix in the name of the subdirs
    :param subdirs: The subdirectories to be contained by each identical directory
    """
    for n in range(number):
        indexed_dir = os.path.join(root, f"{prefix}{n}")
        if not os.path.exists(indexed_dir):
            os.makedirs(indexed_dir)
        for name in subdirs:
            subdir_path = os.path.join(root, f"{prefix}{n}", name)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path)

def distribute_workload(input_dir, output_root, workers_number: int, subdirs_name="batch", ):
    """
    Takes an input directory filled with files, each containing one or multiple pubtator documents. Then creates
    workers_number subdirectories in output_root and distributes the documents equally among them.
    The files in input_dir will be copied.
    :param input_dir: dictionary containing the files to be distributed (single pubtator document or multiple in one)
    :param output_root: path where the the subdirectories for every worker will be created
    :param workers_number: the number of workers to distribute the workload on
    :param subdirs_name: the prefix to the batch subdirs
    """
    # create subdirectories
    tmp_path = os.path.join(output_root, "tmp")
    os.makedirs(tmp_path)
    create_parallel_dirs(output_root, workers_number, subdirs_name)
    paths = (os.path.join(input_dir, file) for file in os.listdir(input_dir))
    file_sizes = {path: os.path.getsize(path) for path in paths if os.path.isfile(path)}
    total_workload = sum(file_sizes.values())
    workload_per_worker = total_workload // (workers_number - 1)

    current_worker_id = 0
    current_worker_workload = 0
    for file, file_size in file_sizes.items():
        # TODO: check after adding -> too much workload, checking before adding -> leftover workload. to be fixed
        if file_size < workload_per_worker:
            copy(file, os.path.join(output_root, f"{subdirs_name}{current_worker_id}"))
            current_worker_workload += file_size
            if current_worker_workload > workload_per_worker:
                current_worker_id = (current_worker_id + 1) % workers_number
                current_worker_workload = 0
        else:
            avg_size_per_doc = file_size // count_documents(file)
            batch_size = workload_per_worker // avg_size_per_doc
            split(file, tmp_path, batch_size)
            current_worker_id = (current_worker_id + 1) % workers_number
            for batch in os.listdir(tmp_path):
                batch = os.path.join(tmp_path, batch)
                os.rename(batch,
                          os.path.join(output_root, f"{subdirs_name}{current_worker_id}", os.path.basename(batch)))
                current_worker_id = (current_worker_id + 1) % workers_number
            current_worker_workload = 0