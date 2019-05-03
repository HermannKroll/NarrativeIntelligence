import os
import subprocess
from time import sleep

from preprocessing.config import Config


def tag_chemicals_diseases(config, input_dir, output_dir, log_dir):
    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    for f in files:
        with open(os.path.join(log_dir, "{}.log".format(f)), "w") as f_log:
            input_file = os.path.join(input_dir, f)
            output_file = os.path.join(output_dir, f)
            command = "{} PubTator {} {} {}".format(config.tagger_one_script, config.tagger_one_model, input_file,
                                                    output_file)
            sp_args = ["/bin/bash", "-c", command]
            process = subprocess.Popen(sp_args, cwd=config.tagger_one_root, stdout=f_log, stderr=f_log)
            # print("DEBUG: {}".format(process.args))
            while process.poll() is None:
                sleep(5)
            print("INFO: TaggerOne thread for {} exited with code {}".format(f, process.poll()))
            if process.poll() == -9:
                print("INFO: Stopping TaggerOne ...")
                break


def tag_genes(config: Config, input_dir, output_dir, log_dir):
    with open(os.path.join(log_dir, "gnorm.log"), "w") as f_log:
        sp_args = ["java", "-Xmx100G", "-Xms30G", "-jar", config.gnorm_jar, input_dir, output_dir, config.gnorm_setup]
        process = subprocess.Popen(sp_args, cwd=config.gnorm_root, stdout=f_log, stderr=f_log)
        # print("DEBUG: {}".format(process.args))
        while process.poll() is None:
            sleep(5)
        print("INFO: GNormPlus exited with code {}".format(process.poll()))
