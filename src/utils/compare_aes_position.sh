#!/bin/bash

# * About

# Print the AES position from recorded signal comparing multiple configuration.

# * Configuration

# set -e
source env.sh

export SR=24e6

# * Script

# ** Initialization

# ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG listen "$ENVRC_NF_FREQ" "$ENVRC_FF_FREQ" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=4 --gain=76 >/dev/null 2>&1 &
# sleep 20

echo "$(date)" > output.log

# ** Instrumentation functions

function config() {
    param_name="$1"
    param_value="$2"
    echo "$1=$2" | tee -a output.log
    sed -i "s/$1 = .*/$1 = $2/g" "$ENVRC_CONFIG_FILE"
}

function instrument() {
    ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG listen "$ENVRC_NF_FREQ" "$ENVRC_FF_FREQ" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=4 --gain=76 & # >/dev/null 2>&1 &
    sleep 15
    ./radio.py --dir "$ENVRC_RADIO_DIR" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config example # >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo "INSTRUMENTATION ERROR" > /tmp/radio-extract.log
    else
        ./radio.py --dir "$ENVRC_RADIO_DIR" extract "$SR" 0 --no-plot --no-overwrite --no-exit-on-error --config 1_aes_weak 2>&1 | tee /tmp/radio-extract.log
        cat /tmp/radio-extract.log | grep -E "Position|ERROR" >> output.log
    fi
    ./radio.py quit # >/dev/null 2>&1
}

# ** Instrumentation script

# *** Compare connection events

function compare_connection_events() {
    config start_radio_conn_event 1
    
    config ll_enc_req_conn_event 6
    for i in $(seq 1 1 5); do
        instrument
    done

    config ll_enc_req_conn_event 9
    for i in $(seq 1 1 5); do
        instrument
    done

    config ll_enc_req_conn_event 12
    for i in $(seq 1 1 5); do
        instrument
    done

    config ll_enc_req_conn_event 16
    for i in $(seq 1 1 5); do
        instrument
    done
}

# compare_connection_events

# *** Compare hop intervals

function compare_hop_intervals() {
    config start_radio_conn_event 1
    config ll_enc_req_conn_event 16
    
    config hop_interval 40
    for i in $(seq 1 1 3); do
        instrument
    done

    config hop_interval 56
    for i in $(seq 1 1 3); do
        instrument
    done

    config hop_interval 72
    for i in $(seq 1 1 3); do
        instrument
    done

}

compare_hop_intervals

# ** Deinit

# ./radio.py quit >/dev/null 2>&1
