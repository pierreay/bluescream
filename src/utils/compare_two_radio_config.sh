#!/bin/bash

set -e
source env.sh

# Number of iterations.
ITER=0

# $1 is the parameter to modify.
function record_all() {
    log_info listen
    ./radio.py --dir $ENVRC_RADIO_DIR listen $ENVRC_NF_FREQ $ENVRC_FF_FREQ $ENVRC_SAMP_RATE --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=$ENVRC_DURATION --gain=$1 &
    sleep 5
    log_info instrument
    ./radio.py --dir $ENVRC_RADIO_DIR instrument $ENVRC_DATASET_RAW_PATH attack $ENVRC_ATTACKER_ADDR $ENVRC_VICTIM_ADDR $ENVRC_VICTIM_PORT $ENVRC_CONFIG_FILE --idx 0 --radio
    log_info extract
    radio_extract INFO --no-plot --overwrite
    log_info to-numpy
    ./radio.py --dir $ENVRC_RADIO_DIR to-numpy /tmp/test_harmonic_$ITER.npy
    log_info quit
    radio_quit
    ITER=$(( ITER + 1))
}

log_info "First recording!"
record_all 73

read -p "Press [ENTER] to continue..."

log_info "Second recording!"
record_all 76

log_info "Plot results..."
./radio.py plot-file $ENVRC_SAMP_RATE /tmp/test_harmonic_0.npy --npy &
./radio.py plot-file $ENVRC_SAMP_RATE /tmp/test_harmonic_1.npy --npy
