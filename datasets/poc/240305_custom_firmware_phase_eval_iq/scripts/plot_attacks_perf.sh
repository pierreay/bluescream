#!/bin/bash

# * About

# Perform multiple attacks and store the results in a CSV file.

# * Global configuration

# Dataset path.
DATASET=$REPO_DATASET_PATH/poc/240305_custom_firmware_phase_eval_iq
# Attack set path.
ATTACK_SET=$DATASET/attack

# Length of the profile in samples.
PROFILE_LENGTH=0
# Start index for attack traces.
START_POINT=0
# Stop index for attack traces.
# END_POINT=$((START_POINT + PROFILE_LENGTH))
END_POINT=0

# Path of script directory.
SCRIPT_WD="$(dirname $(realpath $0))"

# * Functions for CSV building

function iterate() {
    i_start=$1
    i_step=$2
    i_end=$(($3 - 1 ))
    # Iteration over number of traces.
    for num_traces in $(seq $i_start $i_step $i_end); do
        # Write number of traces.
        echo -n "$num_traces;" | tee -a "$OUTFILE_CSV"

        # Attack and extract:
        # 1) The key rank
        # 2) The correct number of bytes.
        sc-attack --no-plot --norm --data-path $ATTACK_SET --start-point $START_POINT --end-point $END_POINT --num-traces $num_traces --comp $COMPTYPE \
                  attack $PROFILE --attack-algo pcc --variable p_xor_k --align --fs 8e6 2>/dev/null \
            | grep -E 'actual rounded|CORRECT' \
            | cut -f 2 -d ':' \
            | tr -d ' ' \
            | tr '[\n]' '[;]' \
            | sed 's/2^//' \
            | sed 's/;$//' \
            | tee -a "$OUTFILE_CSV"

        echo "" | tee -a "$OUTFILE_CSV"
    done
}

# Progressive steps.

# 1 minutes version:
function iterate_very_short() {
    iterate 10 10 100
}

# 25 minutes version:
function iterate_short() {
    iterate 10 10 100
    iterate 100 100 1000
    iterate 1000 200 2000
    iterate 2000 500 $((15000 + 1))
}

# 1h30 version:
function iterate_long() {
    iterate 10 10 1000
    iterate 1000 100 10000
    iterate 10000 250 $((15000 + 1))
}

# 3h version:
function iterate_very_long() {
    iterate 10 5 1000
    iterate 1000 50 10000
    iterate 10000 125 $((15000 + 1))
}

# All traces
function iterate_all() {
    iterate 10 1 200
}

function csv_build() {
    # Write CSV header.
    echo "trace_nb;log2(key_rank);correct_bytes" > "$OUTFILE_CSV"
    # Get data into CSV.
    iterate_all
    # iterate_very_short
    # iterate_short
    # iterate_long
    # iterate_very_long
}

# * Script

function attack_given_profile() {
    # Configuration.
    # Profile configuration.
    export PROFILE_CONFIG=$1
    # Attacked component.
    export COMPTYPE=$2
    # Profile path.
    export PROFILE=$DATASET/profile_${PROFILE_CONFIG}
    # Output CSV file for Python.
    export OUTFILE_CSV=$DATASET/log/attack_results_${PROFILE_CONFIG}.csv
    # Output PDF file for Python.
    export OUTFILE_PDF=$DATASET/plot/attack_results_${PROFILE_CONFIG}.pdf

    # Script.
    # DONE:
    mkdir -p $DATASET/log
    # csv_build
    # DONE:
    mkdir -p $DATASET/plot
    # $SCRIPT_WD/plot_attacks_perf.py $OUTFILE_CSV $OUTFILE_PDF
}

# DONE:
# attack_given_profile amp_3200 amp
# attack_given_profile phr_3200 phr
# attack_given_profile i_3200 i
# attack_given_profile q_3200 q
# attack_given_profile i_augmented_3200 i_augmented
# attack_given_profile q_augmented_3200 q_augmented
