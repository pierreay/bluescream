#!/bin/bash

# * Variables

# Paths.
DATASET=$REPO_DATASET_PATH/ble/240403_1-leak-pairing-highdist-2.534e9-16e6_raw
LOGFILE_PATH=${DATASET}/logs/attack.log

# Parameters.
PROFILE_LENGTH=1000
START_POINT=2000
END_POINT=$((START_POINT + PROFILE_LENGTH))
PLOT=--no-plot

# Actions.
COMPARE_PNB=1
COMPARE_ANB=1
COMPARE_ALGO=1
COMPARE_POINB=1
COMPARE_COMP=1
COMPARE_EXTPROF=0

# * Functions

function attack() {
    trace_nb=$1
    bruteforce=$2
    profile_path=$DATASET/profile_$3_$5
    comptype=$4
    pois_nb=$5
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

(cd $SC && git checkout feat-recombination)

# Compare number of traces for profile:
if [[ $COMPARE_PNB == 1 ]]; then
    for num_traces in 5000 10000 19000 30000; do
        attack 3000 --no-bruteforce AMPLITUDE_${num_traces}_corr AMPLITUDE 1
    done
fi

# Compare number of traces for attacks:
if [[ $COMPARE_ANB == 1 ]]; then
    for num_traces in 1000 3000 7000 20000; do
        attack ${num_traces} --no-bruteforce AMPLITUDE_10000_corr AMPLITUDE 1
    done
fi

# Compare POIS algorithm:
if [[ $COMPARE_ALGO == 1 ]]; then
    for pois_algo in r snr corr; do
        attack 3000 --no-bruteforce AMPLITUDE_10000_${pois_algo} AMPLITUDE 1
    done
fi

# Compare POIS number:
if [[ $COMPARE_POINB == 1 ]]; then
    for pois_nb in 1 2 3; do
        attack 3000 --no-bruteforce AMPLITUDE_10000_corr AMPLITUDE ${pois_nb}
    done
fi

# Compare components results (including recombination):
if [[ $COMPARE_COMP == 1 ]]; then
    for comp in AMPLITUDE; do
        attack 3000 --no-bruteforce '{}_10000_corr' ${comp} 1
    done
fi

tmux capture-pane -pS - > ${LOGFILE_PATH}

grep -E "=|actual.rounded" "${LOGFILE_PATH}" > ${LOGFILE_PATH/.log/_summary.log}

# * Experimental ad-hoc code

# ** Compare with external resampled profile

# Compare with external profile:
if [[ $COMPARE_EXTPROF == 1 ]]; then
    # NOTE: This experiment implies to disable alignment with the profile in
    # the repository code and align it visually.

    echo "Internal profile:"
    profile_in="$DATASET/profile_AMPLITUDE_10000_r_1"
    $SC_SRC/attack.py --log --plot --norm --dataset-path $DATASET --start-point $START_POINT --end-point $END_POINT --num-traces 3000  --comptype AMPLITUDE \
                      attack --attack-algo pcc --profile ${profile_in} --num-pois 1 --poi-spacing 1 --variable p_xor_k --align

    echo "External profile:"
    START_POINT=2133
    END_POINT=$((START_POINT + PROFILE_LENGTH))
    dataset_ext="$REPO_DATASET_PATH/ble/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw"
    profile_ext="$dataset_ext/profile_AMPLITUDE_65536_resamp_16e6"
    $SC_SRC/attack.py --log --plot --norm --dataset-path $DATASET --start-point $START_POINT --end-point $END_POINT --num-traces 3000  --comptype AMPLITUDE \
                      attack --attack-algo pcc --profile ${profile_ext} --num-pois 1 --poi-spacing 1 --variable p_xor_k --align
fi
