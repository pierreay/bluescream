#!/bin/bash

# * Configuration

# Dataset path.
DATASET=$REPO_DATASET_PATH/240414_1-leak-pairing-highdist-fix-2.533e9-8e6_raw

SCRIPT_WD="$(dirname $(realpath $0))"

# * Script

function plot_profile_config() {
    # Profile configuration.
    PROFILE_CONFIG=$1
    # Profile path.
    PROFILE=$DATASET/profile_${PROFILE_CONFIG}
    # Outfile plot path.
    OUTFILE=$DATASET/plots/profile_${PROFILE_CONFIG}.pdf
    # Python script name.
    pyscript=$(basename $0)
    pyscript=${pyscript/.sh/.py}
    # Plot.
    python3 "${SCRIPT_WD}/${pyscript}" $PROFILE $OUTFILE
}

# DONE: Plot all available profiles:
# plot_profile_config AMPLITUDE_10000_r
# plot_profile_config AMPLITUDE_19000_r
# plot_profile_config PHASE_ROT_10000_r
# plot_profile_config PHASE_ROT_19000_r
