#!/bin/bash

# * Variables

# Paths.
DATASET=$REPO_DATASET_PATH/ble/240413_1-leak-pairing-highdist-fix-2.534e9-8e6_raw
LOGFILE_PATH=${DATASET}/logs/attack.log

# Parameters.
PROFILE_LENGTH=500
START_POINT=1000 # NOTE: Depends on current sampling rate at 8e6.
END_POINT=$((START_POINT + PROFILE_LENGTH))
PLOT=--no-plot

# Actions.
COMPARE_PNB=1
COMPARE_ANB=1
COMPARE_ALGO=1
COMPARE_POINB=1
COMPARE_COMP=1

# * Functions

function attack() {
    trace_nb=$1
    bruteforce=$2
    profile_path=$DATASET/profile_$3_$5
    comptype=$4
    pois_nb=$5
    echo "================================================="
    echo trace_nb=$trace_nb
    echo bruteforce=$bruteforce
    echo profile_path=$profile_path
    echo comptype=$comptype
    echo pois_nb=$pois_nb
    $SC_SRC/attack.py --log $PLOT --norm --dataset-path $DATASET --start-point $START_POINT --end-point $END_POINT --num-traces $trace_nb $bruteforce \
                      attack-recombined --comptype $comptype --attack-algo pcc --profile ${profile_path} --num-pois ${pois_nb} --poi-spacing 1 --variable p_xor_k --align
}

# * Script

if [[ -f ${LOGFILE_PATH} ]]; then
    echo "[!] Attack had already be executed: ${LOGFILE_PATH}"
    exit 0
fi

clear
mkdir -p "${DATASET}/logs"

(cd $SC && git checkout main)

num_traces_train_default=5000
num_traces_attack_default=3000
pois_algo_default=r
pois_nb_default=1

# Compare number of traces for profile:
if [[ $COMPARE_PNB == 1 ]]; then
    num_traces_train_list=(5000)
    for num_traces_train in "${num_traces_train_list[@]}"; do
        attack ${num_traces_attack_default} --no-bruteforce AMPLITUDE_${num_traces_train}_${pois_algo_default} AMPLITUDE ${pois_nb_default}
    done
fi

# Compare number of traces for attacks:
if [[ $COMPARE_ANB == 1 ]]; then
    num_traces_attack_list=(1000 2000 3000)
    for num_traces_attack in "${num_traces_attack_list[@]}"; do
        attack ${num_traces_attack} --no-bruteforce AMPLITUDE_${num_traces_train_default}_${pois_algo_default} AMPLITUDE ${pois_nb_default}
    done
fi

# Compare POIS algorithm:
if [[ $COMPARE_ALGO == 1 ]]; then
    pois_algo_list=(r snr)
    for pois_algo in "${pois_algo_list[@]}"; do
        attack ${num_traces_attack_default} --no-bruteforce AMPLITUDE_${num_traces_train_default}_${pois_algo} AMPLITUDE ${pois_nb_default}
    done
fi

# Compare POIS number:
if [[ $COMPARE_POINB == 1 ]]; then
    pois_nb_list=(1 2)
    for pois_nb in "${pois_nb_list[@]}"; do
        attack ${num_traces_attack_default} --no-bruteforce AMPLITUDE_${num_traces_train_default}_${pois_algo_default} AMPLITUDE ${pois_nb}
    done
fi

# Compare components results (including recombination):
if [[ $COMPARE_COMP == 1 ]]; then
    comp_list=(AMPLITUDE)
    for comp in "${comp_list[@]}"; do
        attack ${num_traces_attack_default} --no-bruteforce '{}'"_${num_traces_train_default}_${pois_algo_default}" ${comp} ${pois_nb}
    done
fi

tmux capture-pane -pS - > ${LOGFILE_PATH}

grep -E "=|actual.rounded" "${LOGFILE_PATH}" > ${LOGFILE_PATH/.log/_summary.log}
