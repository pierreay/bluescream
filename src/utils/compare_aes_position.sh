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

# ** Instrumentation loop

function config_instrument() {
    conn_event="$1"
    echo "conn_event=$conn_event" | tee -a output.log
    sed -i "s/ll_enc_req_conn_event = .*/ll_enc_req_conn_event = $conn_event/g" "$ENVRC_CONFIG_FILE"
}

function instrument() {
    ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG listen "$ENVRC_NF_FREQ" "$ENVRC_FF_FREQ" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=4 --gain=76 & # >/dev/null 2>&1 &
    sleep 15
    ./radio.py --dir "$ENVRC_RADIO_DIR" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config example # >/dev/null 2>&1
    ./radio.py quit # >/dev/null 2>&1
    ./radio.py --dir "$ENVRC_RADIO_DIR" extract "$SR" 0 --no-plot --no-overwrite --no-exit-on-error --config 1_aes_weak 2>&1 | tee /tmp/radio-extract.log
    cat /tmp/radio-extract.log | grep -E "Position|ERROR" >> output.log
}

config_instrument 6
for i in $(seq 1 1 5); do
    instrument
done

config_instrument 9
for i in $(seq 1 1 5); do
    instrument
done

config_instrument 12
for i in $(seq 1 1 5); do
    instrument
done

config_instrument 16
for i in $(seq 1 1 5); do
    instrument
done

# ** Deinit

# ./radio.py quit >/dev/null 2>&1
