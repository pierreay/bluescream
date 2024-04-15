#!/bin/bash

# * Variables

dataset=$REPO_DATASET_PATH/ble/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw

profile_length=500
start_point=1000
end_point=$((start_point + profile_length))
plot=--plot

# * Functions

function attack() {
    trace_nb=$1
    bruteforce=$2
    profile_path=$REPO_DATASET_PATH/ble/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw/profile_$3
    comptype=$4
    echo trace_nb=$trace_nb
    echo bruteforce=$bruteforce
    echo profile_path=$profile_path
    echo comptype=$comptype
    $SC_SRC/attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces $trace_nb $bruteforce --comptype $comptype \
                      attack --attack-algo pcc --profile ${profile_path} --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
}

# * Script

# DONE: Attack using amplitude:
# attack 500 --no-bruteforce AMPLITUDE_16384 AMPLITUDE
# attack 1000 --no-bruteforce AMPLITUDE_16384 AMPLITUDE
# attack 2000 --no-bruteforce AMPLITUDE_16384 AMPLITUDE
# attack 3000 --no-bruteforce AMPLITUDE_16384 AMPLITUDE
# attack 4000 --no-bruteforce AMPLITUDE_16384 AMPLITUDE
# attack 14900 --bruteforce AMPLITUDE_16384 AMPLITUDE

# DONE: Attack using phase rotation:
# attack 16000 --no-bruteforce PHASE_ROT_65536 PHASE_ROT

# * Ad-hoc experiment code

# ** Validate recombination algorithm using previous dataset

function attack() {
    trace_nb=$1
    bruteforce=$2
    profile_path=$REPO_DATASET_PATH/ble/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw/profile_$3
    comptype=$4
    echo trace_nb=$trace_nb
    echo bruteforce=$bruteforce
    echo profile_path=$profile_path
    echo comptype=$comptype
    $SC_SRC/attack.py --log --no-plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces $trace_nb $bruteforce \
                      attack-recombined --comptype $comptype --attack-algo pcc --profile ${profile_path} --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
}

attack 14900 --no-bruteforce '{}_16384' AMPLITUDE
