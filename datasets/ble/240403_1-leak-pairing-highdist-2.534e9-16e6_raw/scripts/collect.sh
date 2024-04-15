#!/bin/bash

# * Variables

# ** Screaming Channels .envrc

export ENVRC_VICTIM_PORT="$(nrfjprog --com | cut - -d " " -f 5)"
export ENVRC_SAMP_RATE=16000000 # 30e6
export ENVRC_DURATION=0.2
export ENVRC_WANTED_TRACE_TRAIN=65536
#export ENVRC_WANTED_TRACE_TRAIN=19000
#export ENVRC_WANTED_TRACE_ATTACK=32768
export ENVRC_WANTED_TRACE_ATTACK=21200
export ENVRC_NF_FREQ=128000000 # 128e6
export ENVRC_FF_FREQ=2534000000 # 2.534e9
export ENVRC_RADIO_DIR="$HOME/storage/tmp"
export ENVRC_DATASET_PATH="$HOME/storage/dataset"
export ENVRC_DATASET_RAW_PATH="$ENVRC_DATASET_PATH/240403_1-leak-pairing-highdist-2.534e9-16e6_raw"
export ENVRC_DATASET_AVG_PATH="$ENVRC_DATASET_PATH/tmp_avg"
export ENVRC_DATASET_EXT_PATH="$ENVRC_DATASET_PATH/tmp_ext"
export ENVRC_NIMBLE_PATH="$HOME/git/screaming_channels_nimble"
export ENVRC_CONFIG_FILE="$ENVRC_DATASET_RAW_PATH/config.toml"
export ENVRC_DURATION=0.1
export ENVRC_VICTIM_ADDR="C2:3E:54:84:5C:4C"
export ENVRC_ATTACKER_ADDR="00:19:0E:19:79:D8"
export ENVRC_NF_ID=-1
export ENVRC_FF_ID=0
export ENVRC_EXTRACT_CONFIG="1_aes_ff_antenna_8msps"
export ENVRC_DEVICE_CONFIG="fast"
export ENVRC_DATASET_INPUT="PAIRING"

# * Functions

function init_config() {
    rm -f $ENVRC_CONFIG_FILE
    cp $SC_SRC/config.toml $ENVRC_CONFIG_FILE
}

# Example:
# config "$ENVRC_CONFIG_FILE" "trg_bp_low" "[0.5e6]"
function config() {
    config_file="$1"
    param_name="$2"
    param_value="$3"
    echo "${config_file}: ${param_name}=${param_value}"
    sed -i "s/${param_name} = .*/${param_name} = ${param_value}/g" "${config_file}"
}

# * Script

init_config
config "$ENVRC_CONFIG_FILE" "accept_snr_min" "4.7"
# config "$ENVRC_CONFIG_FILE" "hop_interval" "16"
# config "$ENVRC_CONFIG_FILE" "ll_enc_req_conn_event" "4"
# config "$ENVRC_CONFIG_FILE" "trg_bp_low" "${TRG_BP_LOW}"
# config "$ENVRC_CONFIG_FILE" "trg_bp_high" "${TRG_BP_HIGH}"

(cd $SC_SRC && ./collect.sh -l INFO -y)
