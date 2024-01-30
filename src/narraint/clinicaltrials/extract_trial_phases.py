import csv
import itertools
import logging
import os
import shutil
import tempfile
from datetime import datetime

import requests
from sqlalchemy import delete

import kgextractiontoolbox.document.document as doc
import kgextractiontoolbox.entitylinking.entity_linking_config as cnf
from kgextractiontoolbox.progress import print_progress_with_eta
from narraint.backend.database import SessionExtended
from narraint.backend.models import DrugDiseaseTrialPhase
from narrant.config import PREPROCESS_CONFIG
from narrant.entitylinking.pharmacy.disease import DiseaseTagger
from narrant.entitylinking.pharmacy.drug import DrugTagger


class ClinicalTrialPhaseExtractor:
    CLINICA_TRIAL_REQUEST = "https://clinicaltrials.gov/api/v2/studies?format=csv&fields=Study+Title%7CNCT+Number%7CStudy+Status%7CConditions%7CInterventions%7CSponsor%7CStudy+Type%7CPhases"

    def __init__(self):
        self.tmp_dir = None
        self.clinical_trial_file = None

    def load_and_extract(self):
        self.tmp_dir = tempfile.mkdtemp()
        logging.info(f'Clinical phases data will be stored temporarily in {self.tmp_dir}')
        self.clinical_trial_file = os.path.join(self.tmp_dir, 'clinical_phases.csv')

        # Step one: fetch clinical trial data
        self.fetch_study_data()

        # Step two: extract all (drug, disease, phase) tuples
        ddp = self.extract_drug_disease_phase_tuples()

        # Step three: put everything into a database table
        ClinicalTrialPhaseExtractor.insert_ddp_tuples_into_db(ddp)

        # ... do stuff with dirpath
        shutil.rmtree(self.tmp_dir)

    def fetch_study_data(self):
        logging.info("Starting the process to fetch all studies.")

        with open(self.clinical_trial_file, "w", newline="", encoding="utf-8") as csv_file:
            logging.debug('Sending request to ClinicalTrials.gov...')
            response = requests.get(
                ClinicalTrialPhaseExtractor.CLINICA_TRIAL_REQUEST,
                params={
                    "pageSize": 10000,
                },
            )
            csv_file.write(response.text)
            while 'x-next-page-token' in response.headers:
                logging.debug('Sending request to ClinicalTrials.gov...')
                response = requests.get(
                    ClinicalTrialPhaseExtractor.CLINICA_TRIAL_REQUEST,
                    params={
                        "pageSize": 10000,
                        "pageToken": response.headers['x-next-page-token'],
                    },
                )
                csv_file.write(response.text)

        logging.info("Finished fetching all studies.")

    @staticmethod
    def retrieve_tags(tagger, text):
        tagged_list = []
        untagged_list = text.split("|")
        for item in untagged_list:
            text_doc = doc.TaggedDocument(title=item, abstract="", id=1)
            tagger.tag_doc(text_doc)
            text_doc.remove_duplicates_and_sort_tags()
            for tag in text_doc.tags:
                tagged_list.append(tag.ent_id)
        return tagged_list

    @staticmethod
    def convert_phase(phases_text):
        phases = phases_text.split('|')
        phase_mapping = {
            'NA': -1,
            'EARLY_PHASE1': 0,
            'PHASE1': 1,
            'PHASE2': 2,
            'PHASE3': 3,
            'PHASE4': 4
        }

        max_value = max(phase_mapping.get(phase, -1) for phase in phases)
        return max_value

    def extract_drug_disease_phase_tuples(self):
        logging.info("Starting the process to extract phases.")
        config = cnf.Config(PREPROCESS_CONFIG)
        config.config["dict"]["min_full_tag_len"] = 3
        dd_phase = {}
        drug_tagger = DrugTagger(**dict(logger=logging, config=config, collection="trial_drugs"))
        drug_tagger.prepare()
        disease_tagger = DiseaseTagger(**dict(logger=logging, config=config, collection="trial_diseases"))
        disease_tagger.prepare()

        with open(self.clinical_trial_file, newline='') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            total_rows = sum(1 for row in csv_reader)
            csvfile.seek(0)
            idx = 0
            start_time = datetime.now()
            for row in csv_reader:
                try:
                    drugs = ClinicalTrialPhaseExtractor.retrieve_tags(drug_tagger, row["Interventions"])
                    diseases = ClinicalTrialPhaseExtractor.retrieve_tags(disease_tagger, row["Conditions"])

                    if not drugs or not diseases:
                        print_progress_with_eta("reading clinical trial rows", idx, total_rows, start_time)
                        idx += 1
                        continue

                    phase = ClinicalTrialPhaseExtractor.convert_phase(row["Phases"])

                    for drug, disease in itertools.product(drugs, diseases):
                        if (drug, disease) in dd_phase and phase > dd_phase[(drug, disease)]:
                            dd_phase[(drug, disease)] = phase
                        elif (drug, disease) not in dd_phase:
                            dd_phase[(drug, disease)] = phase

                except Exception as e:
                    logging.error(f"Error processing row: {row}. Error: {e}")
                print_progress_with_eta("reading clinical trial rows", idx, total_rows, start_time)
                idx += 1

        logging.info(f"Finished extracting phases. Total unique drug-disease pairs: {len(dd_phase)}")
        # Generate final tuples
        ddp = [(drug, disease, phase) for (drug, disease), phase in dd_phase.items()]
        return ddp

    @staticmethod
    def insert_ddp_tuples_into_db(ddp):
        logging.info('Deleting data from table: drug_disease_trial_phase')
        session = SessionExtended.get()
        session.execute(delete(DrugDiseaseTrialPhase))
        session.commit()

        logging.info(f'Inserting {len(ddp)} tuples into database...')
        values = [dict(drug=dr, disease=di, phase=p) for dr, di, p in ddp]
        DrugDiseaseTrialPhase.bulk_insert_values_into_table(session, values)

        logging.info('Finished')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    c = ClinicalTrialPhaseExtractor()
    c.load_and_extract()


if __name__ == "__main__":
    main()
