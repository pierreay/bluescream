#!/bin/bash

# * About

# Print the leakage signal duration from recorded signals comparing multiple
# configuration.

# * Configuration

# set -e
source env.sh

export SR=30e6

# * Script

# ** Initialization

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
    echo "-------" >> output.log
    # Init radio.
    ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG --config "$SCRIPT_CONFIG_FILE" listen "$ENVRC_NF_FREQ" "$ENVRC_FF_FREQ" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=4 --gain=76 &
    sleep 20
    # Instrument.
    ./radio.py --dir "$ENVRC_RADIO_DIR" --config "$SCRIPT_CONFIG_FILE" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config example
    if [[ $? != 0 ]]; then
        echo "INSTRUMENTATION ERROR" | tee -a output.log
    else
        # Save signal.
        ./radio.py --dir "$ENVRC_RADIO_DIR" --config "$SCRIPT_CONFIG_FILE" to-numpy "/tmp/leak.npy"
        # Compute signal ON time.
        python3 << EOF | tee -a output.log
import numpy as np
import lib.plot as libplot
import lib.utils as utils

sig = np.abs(np.load("/tmp/leak.npy"))
nsample = utils.nsample_signal_over_noise(sig, window=1000, max_divider=1.5)
print("nsample={}".format(nsample))
print("%={:.4f}".format(nsample / len(sig) * 100))
print("µs={:.4f}".format(nsample / $SR * 1e6))
EOF
        # Print correlation with AES leak.
        ./radio.py --dir "$ENVRC_RADIO_DIR" --config "$SCRIPT_CONFIG_FILE" extract $SR 0 --no-plot --no-overwrite --no-exit-on-error --config 1_aes_weak --corr ../data/signals/2.548GHz_30Msps_AES_BLE_clean_leak_single.npy 2>&1 \
            | grep -E "Number|Correlation" | tee -a output.log
    fi
    # Quit radio.
    ./radio.py quit
}

# ** Instrumentation script

# *** Compare procedure interleaving methods

function compare_procedure_interleaving_methods() {
    echo "=======" >> output.log
    config start_radio_conn_event 1
    config ll_enc_req_conn_event 16
    config hop_interval 56

    echo "=======" >> output.log
    config more_data_bit 0
    config procedure_interleaving false
    for i in $(seq 1 1 5); do instrument; done

    echo "=======" >> output.log
    config more_data_bit 1
    config procedure_interleaving true
    config procedure_interleaving_method \"att_read_request\"
    for i in $(seq 1 1 5); do instrument; done

    echo "=======" >> output.log
    config more_data_bit 1
    config procedure_interleaving true
    config procedure_interleaving_method \"att_read_multiple_request_2\"
    for i in $(seq 1 1 5); do instrument; done

    echo "=======" >> output.log
    config more_data_bit 1
    config procedure_interleaving true
    config procedure_interleaving_method \"att_read_multiple_request_3\"
    for i in $(seq 1 1 5); do instrument; done

    echo "=======" >> output.log
    config more_data_bit 1
    config procedure_interleaving true
    config procedure_interleaving_method \"att_read_multiple_request_4\"
    for i in $(seq 1 1 5); do instrument; done

    echo "=======" >> output.log
    config more_data_bit 1
    config procedure_interleaving true
    config procedure_interleaving_method \"att_find_information_request\"
    for i in $(seq 1 1 5); do instrument; done
}

compare_procedure_interleaving_methods
