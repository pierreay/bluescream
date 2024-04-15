#!/bin/bash

# * Configuration

# Dataset path.
DATASET=$REPO_DATASET_PATH/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw

SCRIPT_WD="$(dirname $(realpath $0))"

# * Script

function plot_profile_config() {
    # Profile configuration.
    PROFILE_CONFIG=$1
    # Profile path.
    PROFILE=$DATASET/profile_${PROFILE_CONFIG}
    # Outfile plot path.
    OUTFILE=$DATASET/plot/profile_${PROFILE_CONFIG}.pdf
    python3 $SCRIPT_WD/plot_profile.py $PROFILE $OUTFILE
}

# DONE:
# plot_profile_config AMPLITUDE_5000
# DONE:
# plot_profile_config PHASE_ROT_5000

# DONE:
# plot_profile_config AMPLITUDE_16384
# DONE:
# plot_profile_config PHASE_ROT_16384

# DONE:
# plot_profile_config AMPLITUDE_27900
# DONE:
# plot_profile_config PHASE_ROT_27900

# DONE:
# plot_profile_config AMPLITUDE_32768
# DONE:
# plot_profile_config PHASE_ROT_32768

# DONE:
# plot_profile_config AMPLITUDE_65536
# DONE:
# plot_profile_config PHASE_ROT_65536
