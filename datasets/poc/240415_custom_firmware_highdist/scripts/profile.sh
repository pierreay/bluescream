#!/bin/bash

# * Parameters

# Dataset path.
DATASET_PATH="${REPO_DATASET_PATH}/poc/240415_custom_firmware_highdist"

# Path of dataset used to create the profile.
TRAIN_SET="${DATASET_PATH}/train"
# Base path used to store the created profile.
PROFILE_PATH_BASE="${DATASET_PATH}/profile"

# Delimiters. Small window greatly increase profile computation speed.
START_POINT=0
END_POINT=0

# NOTE: Sampling rate is hardcoded in collect_*.sh scripts.
FS=8e6

# * Functions

function profile() {
    # Get parameters.
    comp=$1
    num_traces=$2
    pois_algo=$3
    pois_nb=$4
    # Set parameters.
    profile_path=${PROFILE_PATH_BASE}_${comp}_${num_traces}_${pois_algo}_${pois_nb}
    plot=--no-plot
    save_images=--save-images

    # Safety-guard.
    if [[ -d "${profile_path}" ]]; then
        echo "[!] SKIP: Profile creation: Directory exists: ${profile_path}"
        return 0
    fi
    
    # Initialize directories.
    mkdir -p $profile_path
    # Create the profile.
    sc-attack $plot $save_images --norm --data-path $TRAIN_SET --start-point $START_POINT --end-point $END_POINT --num-traces $num_traces --comp $comp profile $profile_path --pois-algo $pois_algo --num-pois $pois_nb --poi-spacing 2 --variable p_xor_k --align --fs $FS
}

# * Script

comp_list=(amp phr)
num_traces_list=(1500)
pois_algo_list=(r snr)
pois_nb_list=(1 2)

for comp in "${comp_list[@]}"; do
    for num_traces in "${num_traces_list[@]}"; do
        for pois_algo in "${pois_algo_list[@]}"; do
            for pois_nb in "${pois_nb_list[@]}"; do
                profile $comp $num_traces $pois_algo $pois_nb
            done
        done
    done
done
