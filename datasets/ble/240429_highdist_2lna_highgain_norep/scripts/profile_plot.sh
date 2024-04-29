#!/bin/bash

# * Environment

env="$(realpath $(dirname $0))/env.sh"
echo "INFO: Source file: $env"
source "$env"

# Safety-guard.
if [[ -z $ENV_FLAG ]]; then
    echo "ERROR: Environment can't been sourced!"
    exit 1
fi

# * Configuration

# Dataset path.
DATASET=${DATASET_PATH}

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
