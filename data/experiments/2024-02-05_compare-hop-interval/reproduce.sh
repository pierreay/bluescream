#!/bin/bash

# * About

# Print the AES position from recorded signal comparing multiple configuration.

# * Configuration

# set -e
source env.sh

export SR=24e6

# * Script

# ** Script initialization

echo "$(date)" > output.log

# Don't modify project's configuration file.
SCRIPT_CONFIG_FILE="/tmp/$(basename $ENVRC_CONFIG_FILE)"
cp "$ENVRC_CONFIG_FILE" $SCRIPT_CONFIG_FILE

# ** Instrumentation functions

function config() {
    param_name="$1"
    param_value="$2"
    echo "$1=$2" | tee -a output.log
    sed -i "s/$1 = .*/$1 = $2/g" "$SCRIPT_CONFIG_FILE"
}

function instrument() {
    # Init.
    ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG --config "$SCRIPT_CONFIG_FILE" listen "$ENVRC_NF_FREQ" "$ENVRC_FF_FREQ" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=2 --gain=76 & # >/dev/null 2>&1 &
    sleep 15
    # Instrument.
    ./radio.py --dir "$ENVRC_RADIO_DIR" --config "$SCRIPT_CONFIG_FILE" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config example # >/dev/null 2>&1
    # Analyze.
    if [[ $? != 0 ]]; then
        echo "INSTRUMENTATION ERROR" > /tmp/radio-extract.log
    else
        ./radio.py --dir "$ENVRC_RADIO_DIR" --config "$SCRIPT_CONFIG_FILE" extract "$SR" 0 --no-plot --no-overwrite --no-exit-on-error --config 1_aes_weak 2>&1 | tee /tmp/radio-extract.log
        cat /tmp/radio-extract.log | grep -E "Position|ERROR" >> output.log
    fi
    # Deinit.
    ./radio.py quit # >/dev/null 2>&1
}

# ** Instrumentation script

# *** Compare hop intervals

function compare_hop_intervals() {
    config start_radio_conn_event 1
    config ll_enc_req_conn_event 25
    
    config hop_interval 17
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 16
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 15
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 14
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 13
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 12
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 11
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 10
    for i in $(seq 1 1 2); do
        instrument
    done

    config hop_interval 5
    for i in $(seq 1 1 1); do
        instrument
    done

    config hop_interval 1
    for i in $(seq 1 1 1); do
        instrument
    done
}

compare_hop_intervals
