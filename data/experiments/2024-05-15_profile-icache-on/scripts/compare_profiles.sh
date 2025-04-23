#!/bin/bash

# * Environment

env="$(realpath $(dirname $0))/env.sh"
echo "INFO: Source file: $env"
source "$env"

# * Variables

# Dataset path.
if [[ -z $DATASET_PATH ]]; then
    echo "ERROR: DATASET_PATH is unset!"
    exit 1
fi

# * Script

mkdir -p "${DATASET_PATH}/plots"

python3 "${DATASET_PATH}/scripts/compare_profiles.py" \
        "${REPO_EXPE_PATH}/2024-05-15_profile-icache-off/profile/amp_4000_r_1" \
        "${DATASET_PATH}/profile/amp_4000_r_1" \
        plots
