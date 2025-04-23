#!/bin/bash

dataset=$REPO_DATASET_PATH/ble/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw
sp=1190
ep=1270

function profile_comp() {
    comp=$1
    nt=$2
    profile=profiles/${comp}_${nt}
    mkdir -p profiles
    $SC_SRC/attack.py --custom-dtype --plot --save-images --norm --dataset-path $dataset --num-traces $nt --start-point $sp --end-point $ep --comptype $comp profile --pois-algo r --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
    mv $dataset/profile $profile
}

profile_comp AMPLITUDE 65536
