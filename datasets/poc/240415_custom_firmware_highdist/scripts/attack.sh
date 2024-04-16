#!/bin/bash

# * Variables

# ** Configuration for the used profiles

# Dataset path.
DATASET_PATH="${REPO_DATASET_PATH}/poc/240415_custom_firmware_highdist"

# List of parameters for the used profiles.
COMP_LIST=(amp phr)
NUM_TRACES_LIST=(2100)
POIS_ALGO_LIST=(r snr)
POIS_NB_LIST=(1 2)

# Delimiters.
START_POINT=0
END_POINT=0

# NOTE: Sampling rate is hardcoded in collect_*.sh scripts.
FS=8e6

# ** Configuration specific to the attack

NUM_TRACES_ATTACK_LIST=(250 500 1000)

# ** Internals

# Path of dataset used for the attack.
ATTACK_SET="${DATASET_PATH}/attack"

# Base path used to fetch the created profile.
PROFILE_PATH_BASE="${DATASET_PATH}/profile"

# Base path used to store the attack log.
LOG_PATH_BASE="${DATASET_PATH}/logs"

# * Functions

function attack() {
    # Get parameters.
    comp=$1
    num_traces=$2
    pois_algo=$3
    pois_nb=$4
    num_traces_attack=$5
    # Set parameters.
    profile_path=${PROFILE_PATH_BASE}/${comp}_${num_traces}_${pois_algo}_${pois_nb}
    log_path=${LOG_PATH_BASE}/attack_${comp}_${num_traces}_${pois_algo}_${pois_nb}.log
    bruteforce="--no-bruteforce"
    plot="--no-plot"

    # Safety-guard.
    if [[ -d "${log_path}" ]]; then
        echo "[!] SKIP: Attack: File exists: ${log_path}"
        return 0
    fi
    
    # Initialize directories.
    mkdir -p $LOG_PATH_BASE
    # Perform the attack.
    sc-attack $plot --norm --data-path $ATTACK_SET --start-point $START_POINT \
              --end-point $END_POINT --num-traces $num_traces_attack $bruteforce --comp $comp \
              attack $profile_path --attack-algo pcc --variable p_xor_k --align --fs $FS \
              | tee $log_path
}

# * Script

for comp in "${COMP_LIST[@]}"; do
    for num_traces in "${NUM_TRACES_LIST[@]}"; do
        for pois_algo in "${POIS_ALGO_LIST[@]}"; do
            for pois_nb in "${POIS_NB_LIST[@]}"; do
                for num_traces_attack in "${NUM_TRACES_ATTACK_LIST[@]}"; do
                    attack $comp $num_traces $pois_algo $pois_nb $num_traces_attack
                done
            done
        done
    done
done
