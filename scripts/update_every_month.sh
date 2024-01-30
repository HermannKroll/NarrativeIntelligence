#!/bin/bash

# Update clinical trial phases for drug overviews
python3 ~/NarrativeIntelligence/src/narraint/clinicaltrials/extract_trial_phases.py
if [[ $? != 0 ]]; then
    echo "Previous script returned exit code != 0 -> Stopping pipeline."
    exit -1
fi