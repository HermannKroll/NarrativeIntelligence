import os
import math
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
    distributed_batches=[]
    os.makedirs(tmp_path)
    create_parallel_dirs(output_root, workers_number, subdirs_name)
    paths = (os.path.join(input_dir, file) for file in os.listdir(input_dir))
    file_sizes = {path: os.path.getsize(path) for path in paths if os.path.isfile(path)}
    file_sizes = {file: size for file, size in sorted(file_sizes.items(), key=lambda item: item[1])}
    total_workload = sum(file_sizes.values())
    workload_per_worker = math.ceil(total_workload / workers_number)
    distribution = [[] for i in range(workers_number)]

    for file, size in file_sizes.items():
        if size < workload_per_worker:
            min(distribution, key=lambda l: len(l)).append(file)
        else:
            not_full_workers=[worker for worker in distribution if len(worker)<workload_per_worker]
            docs_per_worker=math.ceil(size/not_full_workers)
            split(file, tmp_path, docs_per_worker)
            batches = (os.path.join(tmp_path, file) for file in os.listdir(tmp_path) if not file in distributed_batches)
            distributed_batches.extend(batches)
            for worker, batch in zip(not_full_workers, batches):
                worker.append(batch)

    for i, worker in enumerate(distribution):
        worker_dir=os.path.join(output_root,f"{subdirs_name}{i}")
        for file in worker:
            if os.path.basename(file) in distributed_batches:
                os.rename(file,os.path.join(output_root,subdirs_name,os.path.basename(file)))
            else:
                copy(file, worker_dir)