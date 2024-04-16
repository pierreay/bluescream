#!/bin/bash

# * Parameters

# Path of dataset used to create the profile.
TRAIN_SET=$REPO_DATASET_PATH/poc/240415_custom_firmware_highdist/train
# Base path used to store the created profile.
PROFILE_PATH_BASE=$TRAIN_SET/../profile
# Path of dataset used to perform the attack.
ATTACK_SET=$REPO_DATASET_PATH/poc/240415_custom_firmware_highdist/attack

# Number of traces to use for profile creation.
NUM_TRACES_PROFILE=16000
# Number of traces to use for attack.
NUM_TRACES_ATTACK=4100
# Delimiters. Small window greatly increase profile computation speed.
START_POINT=0
END_POINT=0

# NOTE: Sampling rate is hardcoded in collect_*.sh scripts.
FS=8e6

# * Functions

function profile_comp() {
    # Get parameters.
    comp=$1

    # Iterate over good POI algorithms.
    for pois_algo in snr t r corr 
    do
        echo "pois_algo=$pois_algo"
        # Set global parameters.
        export PROFILE_PATH=${PROFILE_PATH_BASE}_${comp}_${NUM_TRACES_PROFILE}_${pois_algo}
        # Initialize directories.
        mkdir -p $PROFILE_PATH
        # Create the profile.
        profile $pois_algo
    done
    
    # Check result.
    if [[ ! -f $PROFILE_PATH/PROFILE_MEAN_TRACE.npy ]]; then
        echo "Profile has not been created! (no file at $PROFILE_PATH/*.npy)"
        exit 1
    fi
}

function profile() {
    # Get parameters.
    pois_algo=$1
    # Print options.
    plot=--no-plot
    echo "plot=$plot"
    save_images=--save-images
    echo "save_images=$save_images"
    # Profile.
    sc-attack $plot $save_images --norm --data-path $TRAIN_SET --start-point $START_POINT --end-point $END_POINT --num-traces $NUM_TRACES_PROFILE --comp $comp profile $PROFILE_PATH --pois-algo $pois_algo --num-pois 1 --poi-spacing 2 --variable p_xor_k --align --fs $FS
}

function attack_comp() {
    # Get parameters.
    comp=$1

    # Attack only successful profiles (good correlations + good POIs values).
    for pois_algo in snr corr
    do
        echo "pois_algo=$pois_algo"
        # Set global parameters.
        export PROFILE_PATH=${PROFILE_PATH_BASE}_${comp}_${NUM_TRACES_PROFILE}_${pois_algo}
        # Perform the attack.
        echo "Attack '$comp' with profile: $PROFILE_PATH"
        attack
    done
}

function attack() {
    # bruteforce="--bruteforce"
    # plot="--plot"
    sc-attack $plot --norm --data-path $ATTACK_SET --start-point $START_POINT --end-point $END_POINT --num-traces $NUM_TRACES_ATTACK $bruteforce --comp $comp \
              attack $PROFILE_PATH --attack-algo pcc --variable p_xor_k --align --fs $FS
}

# * Script

# ** Profiles

profile_comp amp
profile_comp phr

# ** Attacks

# DONE: Attack using previously created templates.
# attack_comp amp
# attack_comp phr
# attack_comp i_augmented
# attack_comp q_augmented
